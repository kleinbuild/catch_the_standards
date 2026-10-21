# catch_the_standards

A tool for special education teachers (and gen ed teachers who need to provide focused individual support or contribute their expertise to IEP development). Given a grade-level California standard a student is missing, find the prerequisite standards and skills to spiral instruction and IEP goals back through, across grades. Bridge ELA and ELD standards for dual-identified students (IEP + English learner).

The owner is a teacher building this while learning the tooling. When a new library, command, or concept comes up, say what it is and why it's being used, in a sentence or two. Prefer small, runnable steps over large drops of code.

When asked to document what was learned, write it as working notes: claim, then the specific evidence, in the order that matters. No headers or bolded takeaways in those notes, no rhetorical openers, no inflating language. Leave out claims that nothing specific supports.


## Environment

- Development happens on two machines:
  - Windows, project at `H:\MyApps\catch_the_standards`. Git Bash (MINGW64) is the preferred shell (`/h/MyApps/catch_the_standards`), by choice; PowerShell and Command Prompt are also used. Give Git Bash commands by default, and note where PowerShell or cmd differ.
  - Debian 13 (Q4OS) laptop, project at `/home/jamesk/Documents/myApps/catch_the_standards/`. Debian 13's packaged Python is 3.13.
- macOS is a required target: most end users are expected to be on Mac. It is not a development machine; a borrowed Mac is available for testing. Code must run unchanged on Windows, Linux, and macOS: build paths with `pathlib`, don't call shell commands from Python, and open text files with an explicit `encoding="utf-8"` (Windows defaults to cp1252).
- Python 3.14 in a project venv, `.venv`. The Windows machine also has a Microsoft Store Python 3.12 that `python3` can resolve to, so always activate the venv and use `python -m pip`, never bare `pip`. See docs/decisions/0008.
- Setup:
  ```bash
  bash scripts/setup_venv.sh                                         # Git Bash, Linux, macOS
  powershell -ExecutionPolicy Bypass -File scripts\setup_venv.ps1    # PowerShell or cmd
  ```
- Activate:
  ```
  source .venv/Scripts/activate      # Git Bash on Windows
  .\.venv\Scripts\Activate.ps1       # PowerShell
  .venv\Scripts\activate.bat         # Command Prompt
  source .venv/bin/activate          # Linux, macOS
  ```
- Scripts that fetch from www2.cde.ca.gov must run on the owner's machine. A Claude cloud workspace could not reach the site (connection refused by its proxy, 2026-10-08).
- GitHub at https://github.com/kleinbuild/catch_the_standards; download repo with GitHub CLI using `gh repo clone kleinbuild/catch_the_standards`; or with HTTPS via https://github.com/kleinbuild/catch_the_standards.git.

## Layout

```
CLAUDE.md, README.md, requirements.txt, .gitignore
docs/decisions/    one file per decision, numbered; read these before changing data handling
docs/reference/    glossary.md (project terms); generated CACS_URL_REFERENCE.md, codes.csv, codes.json
scripts/           scrape_cacs_records.py (subject-page HTML to one row per CDE record; the standards source, 0011)
                   match_csv_to_records.py (pairs dl=1 CSV rows with scraped records; not yet committed)
                   probe_cacs_ids.py (fetch one HTML results page and report record links and symbols)
                   cacs_codes.py (discover filter codes), compare_cacs.py (subject vs search-all downloads; ELA only, 0001)
                   math_cross_domain_check.py, show_rows.py (exploratory checks on the math dl=1 CSV)
                   setup_venv.sh, setup_venv.ps1 (create .venv and install requirements)
src/               schema.sql, load.py (not written yet)
data/raw/          scraped records files (UTF-8) and dl=1 CSV downloads (cp1252), committed, named with date
data/curated/      hand-reviewed data: concepts, reviewed edges. The owner's expert work.
data/build/        standards.db, rebuilt by load.py, never committed
tests/
```


## Rules

- Standards are loaded from the per-subject pages' HTML results (`/cacs/<subject>?...&dl=0`), scraped by `scripts/scrape_cacs_records.py`. The `dl=1` CSV is a cross-check only. `/cacs/all` is for cross-subject text search only. (0001, 0011)
- Identify standards by CDE record ID, never by identifier alone: identifiers repeat across math courses. (0011)
- Never edit `data/build/standards.db` by hand. Change the inputs in `data/raw` or `data/curated` and rebuild. (0007)
- Never overwrite or reorder rows in `data/curated/`. Add rows; mark machine-generated rows `reviewed=0` with a `source` value. Only the owner sets `reviewed=1`.
- Keep CDE's own codes and record IDs (e.g. `/cacs/id/web/5531`) on every row, even where we normalize (cluster alias, grade ranges), so any row can be traced back to the site.
- Similarity (shared words, embeddings) never becomes a prerequisite edge on its own. It can only produce unreviewed suggestions. (0006)
- Wait at least 1 second between requests to the CDE site.


## CDE site facts (details and evidence in docs/decisions)

- Download URL: `https://www2.cde.ca.gov/cacs/<subject>?c0=&c1=&c2=&order=0&page=0&perpage=100&mingrade=0&maxgrade=12&dl=1`. `dl=1` returns the whole result set as one CSV regardless of `perpage`. (0002)
- `mingrade`/`maxgrade` both default to 0, which means kindergarten only. Always set `maxgrade=12`. (0002)
- c0/c1/c2 codes are per subject page; they are not shared across subjects. `/cacs/all` has its own `carea` codes (ELA=7, ELD=10, Math=2, Science=13, CTE 11/12) and its own `order` codes. (0002)
- ELA cluster code 3 "Conventions of Standards English" is a misspelled duplicate of code 2 covering only grades 6–8. Treat 3 as 2. (0003)
- Scrape URL: `https://www2.cde.ca.gov/cacs/<subject>?mingrade=0&maxgrade=12&order=0&page=<n>&perpage=100&dl=0`, paging from 0. The HTML is UTF-8 and links each record to `/cacs/id/web/<record ID>`. (0011)
- The `dl=1` CSV has no record IDs and is cp1252: it writes "?" for the minus sign (U+2212) and not-equal sign. (0011)
- Math identifiers are not unique: high school standards repeat once per course (A-CED.1 in five courses), and Calculus.16.0 is two standards in one course. ELA identifiers are unique. (0011)
- High school standards carry grade ranges ("9–10", en dash). Store `grade_min`/`grade_max`. (0004)
- Identifiers mix en dashes and hyphens: RH, RST, WHST, and high school ELD write the grade band with an en dash (RH.6–8.1, ELD.PI.9–10.1.Br); other ELA identifiers use a hyphen (L.9-10.1). Store as written plus a hyphen-normalized copy. In text, subtraction is written with the minus sign or the en dash. (0012)
- ELD identifiers look like `ELD.PI.K.12b.Em`; each proficiency level (Em/Ex/Br) is a separate record. (0005)
- `/cacs/eld` holds ELD Part I (507 records) and Part II (264), and no Part III. (0005, 0011)


## Current state (2026-10-20)

Done: bulk download per subject works; filter codes discovered and documented; subject vs search-all comparison run for ELA.
Bulk downloaded CSV for ELA, ELD, and Math CA standards.
Setup scripts for the venv written for Git Bash/Linux/macOS and PowerShell; macOS path not yet tested.
Scraped records for math, ELA, and ELD; every dl=1 CSV row paired with one scraped record (0011).

Next: commit `scripts/match_csv_to_records.py`. Then write `src/schema.sql` and `src/load.py` (records files to SQLite keyed by record ID, identifier parsing, structural progression edges), following 0011 and 0012.

Open questions:
- What the search-all download's Main Category corresponds to (not checked).
- Whether to commit the fetched HTML pages next to each records file. (0011)
- A progression rule for high school math, where identifiers carry no grade. (0005)
- Whether `query=a` on `/cacs/all` matches every standard in subjects other than ELA.
- Whether ELD Part III, which `/cacs/eld` does not have, exists anywhere in a form usable for ELD-to-ELA bridge edges. The published CA ELD Standards document is the first place to check; it is also believed, not checked, to have ELD-to-ELA correspondence tables usable as official bridge edges.
- Availability and licensing of Dynamic Learning Maps, Core Content Connectors, and the Achieve the Core coherence map as prerequisite sources (not checked).
- How end users on macOS will get the tool: installing Python and running the setup script, a packaged app, or a hosted web page. The setup scripts are for development and assume comfort with a terminal.
- Whether Python 3.13 (Debian 13's version) is acceptable on the laptop, or 3.14 should be installed there.
