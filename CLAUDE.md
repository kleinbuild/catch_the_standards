# catch_the_standards

A tool for special education teachers (and gen ed teachers who need to provide focused individual support or contribute their expertise to IEP development). Given a grade-level California standard a student is missing, find the prerequisite standards and skills to spiral instruction and IEP goals back through, across grades. Bridge ELA and ELD standards for dual-identified students (IEP + English learner).

The owner is a teacher building this while learning the tooling. When a new library, command, or concept comes up, say what it is and why it's being used, in a sentence or two. Prefer small, runnable steps over large drops of code.

When asked to document what was learned, write it as working notes: claim, then the specific evidence, in the order that matters. No headers or bolded takeaways in those notes, no rhetorical openers, no inflating language. Leave out claims that nothing specific supports.


## Environment

- Windows, Git Bash (MINGW64). Project at `H:\MyApps\catch_the_standards` (`/h/MyApps/catch_the_standards` in Git Bash).
- Linux Debian 13 (Q4OS) on a small laptop. Project at `/home/jamesk/Documents/myApps/catch_the_standards/` 
- Python 3.14 in a project venv. The machine also has a Microsoft Store Python 3.12 that `python3` can resolve to, so always activate the venv and use `python -m pip`, never bare `pip`. See docs/decisions/0008.
- Setup:
  ```bash
  py -3.14 -m venv .venv
  source .venv/Scripts/activate
  python -m pip install -r requirements.txt
  ```
- Scripts that fetch from www2.cde.ca.gov must run on the owner's machine. A Claude cloud workspace could not reach the site (connection refused by its proxy, 2026-10-08).
- GitHub at https://github.com/kleinbuild/catch_the_standards; download repo with GitHub CLI using `gh repo clone kleinbuild/catch_the_standards`; or with HTTPS via https://github.com/kleinbuild/catch_the_standards.git.

## Layout

```
CLAUDE.md, README.md, requirements.txt, .gitignore
docs/glossary.md   project terms and their meanings; read before writing code, data, or decisions
docs/decisions/    one file per decision, numbered; read these before changing data handling
docs/reference/    generated CACS_URL_REFERENCE.md, codes.csv, codes.json
scripts/           cacs_codes.py (discover filter codes), compare_cacs.py (subject vs search-all downloads)
src/               schema.sql, load.py (not written yet)
data/raw/          downloaded CDE CSVs, committed, named with download date
data/curated/      hand-reviewed data: concepts, reviewed edges. The owner's expert work.
data/build/        standards.db, rebuilt by load.py, never committed
tests/
```


## Rules

- Use terms as defined in `docs/glossary.md`. To use a term with a new meaning, add or change its glossary entry in the same change.
- The per-subject pages (`/cacs/<subject>?...&dl=1`) are the data source. `/cacs/all` is for cross-subject text search only. (0001)
- Never edit `data/build/standards.db` by hand. Change the inputs in `data/raw` or `data/curated` and rebuild. (0007)
- Never overwrite or reorder rows in `data/curated/`. Add rows; mark machine-generated rows `reviewed=0` with a `source` value. Only the owner sets `reviewed=1`.
- Keep CDE's own codes and record IDs (e.g. `/cacs/id/web/5531`) on every row, even where we normalize (cluster alias, grade ranges), so any row can be traced back to the site.
- Similarity (shared words, embeddings) never becomes a prerequisite edge on its own. It can only produce unreviewed suggestions. (0006)
- Each guidance record keeps the scope its source states (target type, learning stage, population). Never widen that scope when entering, summarizing, or displaying it. The tool shows the records whose scope matches the teacher's situation and never ranks them or picks one method. (0009, proposed)
- Wait at least 1 second between requests to the CDE site.


## CDE site facts (details and evidence in docs/decisions)

- Download URL: `https://www2.cde.ca.gov/cacs/<subject>?c0=&c1=&c2=&order=0&page=0&perpage=100&mingrade=0&maxgrade=12&dl=1`. `dl=1` returns the whole result set as one CSV regardless of `perpage`. (0002)
- `mingrade`/`maxgrade` both default to 0, which means kindergarten only. Always set `maxgrade=12`. (0002)
- c0/c1/c2 codes are per subject page; they are not shared across subjects. `/cacs/all` has its own `carea` codes (ELA=7, ELD=10, Math=2, Science=13, CTE 11/12) and its own `order` codes. (0002)
- ELA cluster code 3 "Conventions of Standards English" is a misspelled duplicate of code 2 covering only grades 6–8. Treat 3 as 2. (0003)
- High school standards carry grade ranges ("9–10", en dash). Store `grade_min`/`grade_max`. (0004)
- ELD identifiers look like `ELD.PI.K.12b.Em`; each proficiency level (Em/Ex/Br) is a separate record. (0005)


## Current state (2026-10-13)

Done: bulk download per subject works; filter codes discovered and documented; subject vs search-all comparison run for ELA.
Bulk downloaded CSV for ELA, ELD, and Math CA standards.

Next: write `src/schema.sql` and `src/load.py` (CSVs to SQLite, identifier parsing, structural progression edges). Needs the header row and 2–3 sample rows from an ELA download and an ELD download to set the parsing rules.

Open questions:
- Exact column names in the subject-page CSVs. Known so far: ELA download has 9 columns including Subject Area, Domain, Cluster. Search-all download has 7, including Main Category. Not yet checked what Main Category corresponds to.
- Whether `/cacs/eld` contains all of ELD Parts I, II, and III. `/cacs/all` says some standards "have not yet been added to this system."
- Whether `query=a` on `/cacs/all` matches every standard in subjects other than ELA.
- Whether the published CA ELD Standards document has ELD-to-ELA correspondence tables usable as official bridge edges (believed, not checked).
- Availability and licensing of Dynamic Learning Maps, Core Content Connectors, and the Achieve the Core coherence map as prerequisite sources (not checked).
