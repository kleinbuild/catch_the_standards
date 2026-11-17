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
docs/design/       ui-options.md (first thoughts on the interface and how teachers get the tool; the owner's answers)
                   prototype/ (index.html, app.js, data.js: three standards in two layouts; open index.html by double-click)
docs/reference/    glossary.md (project terms); generated CACS_URL_REFERENCE.md, codes.csv, codes.json
scripts/           scrape_cacs_records.py (subject-page HTML to one row per CDE record; the standards source, 0011)
                   match_csv_to_records.py (pairs dl=1 CSV rows with scraped records)
                   probe_cacs_ids.py (fetch one HTML results page and report record links and symbols)
                   join_learning_commons.py (pairs CDE records with Learning Commons items; imports math builds-towards links; writes data/derived/)
                   make_review_sheets.py (writes the owner's review sheets to data/curated/review/; adds rows, never changes them)
                   make_prototype_data.py (copies three standards out of the database into docs/design/prototype/data.js)
                   cacs_codes.py (discover filter codes), compare_cacs.py (subject vs search-all downloads; ELA only, 0001)
                   math_cross_domain_check.py, show_rows.py (exploratory checks on the math dl=1 CSV)
                   setup_venv.sh, setup_venv.ps1 (create .venv and install requirements)
src/               schema.sql (tables), load.py (rebuilds data/build/standards.db; standard library only)
                   lookup.py (what a standard builds on: `python src/lookup.py L.5.1b`)
data/raw/          scraped records files (UTF-8) and dl=1 CSV downloads (cp1252), committed, named with date
data/curated/      hand-reviewed data: identifier_corrections.csv; later concepts and reviewed edges. The owner's expert work.
data/derived/      output of join_learning_commons.py, committed: IDs and codes, no standards text. Regenerated, not hand-edited.
data/build/        standards.db, rebuilt by load.py, never committed
tests/             test_load.py, test_join.py, test_lookup.py; run with `python -m unittest discover tests`
```


## Rules

- Standards are loaded from the per-subject pages' HTML results (`/cacs/<subject>?...&dl=0`), scraped by `scripts/scrape_cacs_records.py`. The `dl=1` CSV is a cross-check only. `/cacs/all` is for cross-subject text search only. (0001, 0011)
- Identify standards by CDE record ID, never by identifier alone: identifiers repeat across math courses. (0011)
- Never edit `data/build/standards.db` by hand. Change the inputs in `data/raw` or `data/curated` and rebuild. (0007)
- Never overwrite or reorder rows in `data/curated/`. Add rows; mark machine-generated rows `reviewed=0` with a `source` value. Only the owner sets `reviewed=1`.
- Keep CDE's own codes and record IDs (e.g. `/cacs/id/web/5531`) on every row, even where we normalize (cluster alias, grade ranges), so any row can be traced back to the site.
- Similarity (shared words, embeddings) never becomes a prerequisite edge on its own. It can only produce unreviewed suggestions. (0006)
- Wait at least 1 second between requests to the CDE site.
- This repo is public. Never commit PDFs or other third-party source documents here. If one must be committed for development, it goes only in the private `catch_standards` repo. Bulk third-party datasets (Learning Commons) are committed to neither; they live in a folder beside the two repos on each development machine.
- Imported relationships from any outside dataset arrive `reviewed=0` with their own `source` value, like any machine-generated row.
- The loader stores CDE's text and identifiers as written and does not repair them. Repairs to malformed identifiers and missing parent standards come only from a public dataset, recorded with its source.


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


## Pick up here (written 2026-11-14 for the next session)

The first slice of the data work is finished and the owner wants to move to interface design and a prototype. Read `docs/design/ui-options.md` first: it holds Claude's first thoughts on delivery (a web page with the database inside it is recommended), on how to draw the prerequisite view, and six questions for the owner whose answers shape the design. The suggested first step is that the owner answers those questions and Claude builds one HTML file with real data for three standards in two layouts.

To see the current tool on this machine:
```bash
python src/load.py                                # rebuild data/build/standards.db
python src/lookup.py 4.NF.3.a --components        # math: prerequisites, parent standard, learning components
python src/lookup.py L.5.1b                       # ELA: progression, sub-item b marked, ELD standards that list it
python src/lookup.py ELD.PI.4.6a.Ex               # ELD: earlier grade, lower level, ELA standards listed against it
python -m unittest discover tests                 # 83 tests
```
None of these needs the venv; they use only Python's standard library.

Waiting on the owner:
- Marking the review sheets in `data/curated/review/` (how: the README there), starting 2026-11-15. No row is marked yet. The seven rows of `data/curated/identifier_corrections.csv` are also `reviewed=0`.
- Merging `build/loader` into `main`. No pull request has been opened. `main` is 12 commits behind.
- On the Debian laptop: `git fetch origin && git switch main && git reset --hard origin/main`, not `git pull`. The laptop still has the commit that held `ccssmgraph.pdf`, and a pull would merge it back.
- Asking GitHub Support to remove unreachable commit 20bc256 from `kleinbuild/catch_the_standards`, if the owner wants the PDF gone for good.
- Whether `cacs_probe/` stays in the repo.

To refresh from a new Learning Commons release: put the files in `learning_commons/open-knowledge-graph/` beside the repo, then run `python src/load.py`, `python scripts/join_learning_commons.py`, `python src/load.py` again, and `python scripts/make_review_sheets.py`. The first load gives the join script the records; the second picks up what the join wrote. The join script reads about 1 GB and takes under a minute.

## Current state (2026-11-14)

Work is on branch `build/loader` here (pushed) and `dev/private-sources` in the private repo (local, nothing committed on it).

Done:
- `python src/load.py` builds `data/build/standards.db` keyed by record ID: 734 math, 568 ELA, 771 ELD records, 480 ELA sub-items, 63 parent standards that have no CDE record (added from Learning Commons, with negative `record_id` and `origin='learning_commons'`), and 2,851 edges (1,187 `next_grade` and 514 `next_level` structural; 1,150 `builds_towards` from Learning Commons). No edge is reviewed.
- `python scripts/join_learning_commons.py` pairs CDE records with Learning Commons California items: math 734 of 734, ELA 544 of 568, ELD 771 of 771, and every ELA sub-item. Output is in `data/derived/`.
- `python src/lookup.py <identifier>` prints what a standard builds on, with the source of each link.
- `lookup.py` also shows, for an ELD record, the ELA standards listed against its ELD standard, and for an ELA record, the ELD standards that list it.
- `python scripts/make_review_sheets.py` wrote six sheets to `data/curated/review/` (how to mark them: the README there). The loader applies decisions from the link sheets where a row has `reviewed=1`: `keep` marks the link reviewed, or adds it with source `owner` if it was a candidate; `reject` leaves it out. Decisions on `pairings.csv` and `eld_ela_notes.csv` are recorded and not yet acted on.
- Learning components load when their two files are in `data/derived/`: 5,983 components attached in 7,382 places (1,848 math components on 744 records or parent rows; 4,135 ELA components on 200 K–2 records or sub-items). `python src/lookup.py 4.NF.3.a --components` lists them. The owner approved committing both files (1.8 MB together) on 2026-11-14.
- 83 tests pass (`python -m unittest discover tests`).
- The cross-check of CSV rows against scraped records (0011) was re-run on 2026-11-14 with the same counts.

Facts found on 2026-11-14, not yet in a decision record:
- ELA sub-items are not separate records. No ELA identifier has a letter; 139 ELA records hold lettered lines inside `text_Standard`. The loader splits them into `sub_items`, keyed by record ID plus letter. Learning Commons has each as its own item (L.5.1.b).
- Seven identifiers are wrong on the CDE site and are listed with evidence in `data/curated/identifier_corrections.csv`, all `reviewed=0`: RL.2..2, RL.2..3, ELD.PI.12a.Em/Ex/Br (grade 4), ELD.PI.7.78.Em (the owner judged it a typo for 7.8), and the second Calculus.16.0 (record 4763), whose text is Learning Commons' 17.0. The loader keeps the identifier as written and reads the parts from the correction.
- 24 ELA records are placeholders: their whole text is a note such as "(Begins in grade 2)" or "(Not applicable to literature)". `is_placeholder=1`; progressions skip them.
- CDE lists some math standards only as their parts: 4.NF.3.a, b, c, d but no 4.NF.3. All 158 math sub-item records lacked a parent record: 30 parents in K–8 and 33 across the high school courses. Learning Commons has every one. `join_learning_commons.py` writes them to `data/derived/learning_commons_parents.csv` and the loader adds them as rows, each sub-item record pointing at its parent through `parent_record_id`. (An earlier note here said 30 of 32 K–8 parents were missing; the count of 32 wrongly included 2.NBT.7.1 and 5.OA.2.1, which are California additions, not sub-items.)
- A link Learning Commons publishes to or from such a parent is one edge, on the parent row. Until 2026-11-14 it was copied onto every sub-item record, which turned 138 published links into 624 pairs nobody published. Those pairs are now in `learning_commons_spread_candidates.csv` and are not loaded. `lookup.py` shows a sub-item's parent and follows the parent's links.
- One added parent, 4.NF.3, has LaTeX in its Learning Commons text (`$\frac{a}{b}$`). `plain_math()` in the join script writes it as a/b, as CDE does.
- ELD lettering changes between grades (PI.6 in grade 3 is PI.6a and PI.6b in grade 4). Those `next_grade` edges link every record of the number and carry a note; 48 edges.
- The ELA asterisk footnote is in `text_Footnote` on 13 records. In math the asterisk appears only in high school (216 records), where it marks modeling standards, so `has_asterisk` means different things by subject.
- Two sub-item typos in ELA text: "c . Decode" in RF.2.3 and "d.Review" in SL.4.1. The loader reads them as items c and d.
- The em dash (U+2014) occurs in 33 fields, as punctuation. It is not normalized (0012 left this open).
- Git was converting line endings in the data files on Windows. `.gitattributes` now stores `data/raw/`, `data/curated/`, `data/derived/`, and `cacs_probe/` byte for byte.

Learning Commons Knowledge Graph (docs.learningcommons.org; downloaded 2026-11-14 to a `learning_commons` folder beside the repos; not committed):
- Its item codes are its own, not CDE identifiers. Math codes carry the cluster letter and an HS prefix (3.NF.A.2, HSA-CED.A.1), and California's own additions are written with a dot (HSF.LE.A.4.1). `cde_form()` in the join script rewrites them. High school standards are one item per course, as on the CDE site, plus one copy under no course.
- Its ELD codes have no letter and no proficiency level (ELD.4.I.C.12), so several CDE records share one item.
- Math text agrees for 512 of 734 records and one text contains the other for 173; 49 differ and are marked in `learning_commons_map.csv`. CDE repeats the parent sentence before a sub-item, and one side or the other omits the worked examples.
- 757 `buildsTowards` links (Student Achievement Partners coherence map, CC0) join Common Core math standards. 727 are imported as 1,150 edges: 453 between K–8 rows, one per published link, and 697 with a high school row at one or both ends (more than one per published link, because a standard is one row per course). 30 are not imported and are listed in `learning_commons_edges_unresolved.csv`: for 28 the California item has no CDE record (F-TF.3, N-CN.4, G-GMD.2 and others; why CDE lacks them is not checked), and for 2 no California item is rated the same as the Common Core one.
- High school pairing rule (owner's decision, 2026-11-14): same pathway. Course copies are joined within Algebra I / Geometry / Algebra II and within Math I / II / III, never across. Each later standard is linked from the nearest copy of the earlier standard at or before its own course; a K–8 standard links to every course copy. Treating the course "Statistics and Probability" as following either pathway is an assumption made in the script, not something the owner decided.
- It has no prerequisite links for ELA or ELD.
- Learning components: math ones are attached to California math items and written by Achievement Network; ELA ones are attached to Common Core ELA items for grades K–2, written by Learning Commons, and are followed to the California record or lettered sub-item with the same code (every code matched). A component on a high school standard's course-free copy is attached to each course's record. 220 attachments found no row to land on; which ones has not been looked at. They are kept apart from the owner's concepts list (0006) and carry no role (introduces, develops, expects mastery).
- Each of its 209 California ELD standards has a `notes` field listing ELA standards ("W.4.4–5; SL.4.4, 6; L.4.1, 3, 5–6"); the items give the California State Board of Education as author. The join script splits the notes into 2,084 ELD-standard-to-ELA-record pairs, written to `learning_commons_eld_ela.csv` and loaded into the table `eld_ela_links`, all `reviewed=0`. Three notes read "Not applicable at kindergarten" or "at grade 1" and yield nothing. One piece had a stray space ("WHST. 9-10.4-5") and is read anyway. Every other piece matched exactly one ELA record. No RF standard appears in any note.
- A note belongs to the ELD standard as a whole (part, number, grade), covering every proficiency level and letter, so `eld_ela_links` is keyed that way and is not in `edges`. Between 3 and 43 ELA standards are listed per ELD standard.
- The notes write the grades 6–8 literacy strands by single grade ("RH.6.1–10"), where CDE has one record for grades 6–8 (RH.6–8.1). They are matched by the grade falling inside the record's range.
- A range in a note can cross a placeholder: "RL.9–10.1, 7–9" includes RL.9-10.8, "(Not applicable to literature)". One such pair exists; `lookup.py` leaves placeholders out.
- The notes have not been compared with the published CA ELD Standards document, which is the source they appear to copy.
- Its 284 `relatesTo` links (non-directional) are not imported.

Review stage reached 2026-11-14: the sheets are with the owner and none is marked yet. What each sheet holds: `ela_links.csv` 44 next-grade links whose wording is under 30% alike; `eld_links.csv` 48 links where lettering changes and 9 whose wording is under 30% alike; `math_links.csv` 19 links that jump three or more grades and 45 involving the Statistics and Probability course; `math_link_candidates.csv` the 624 set-aside sub-item pairs; `pairings.csv` 58 records (49 math, 9 ELA) whose text differs from their Learning Commons item; `eld_ela_notes.csv` 206 ELD notes, 22 of them (one per part per grade) marked as the sample to compare with the published CA ELD Standards.

Next: interface design and a prototype (`docs/design/ui-options.md`), and acting on the owner's review decisions as they come.

Open questions:
- Whether the course "Statistics and Probability" should be linked from both pathways, as the join script now does.
- No link from the course Statistics and Probability back to a pathway course exists in the data, so the "either pathway" assumption affects only the 45 links listed in `math_links.csv`.
- Whether learning components should seed the owner's concepts list (0006), or stay a separate reference.
- Links not on any sheet (most of them) stay `reviewed=0`. Whether the owner wants a way to mark whole groups as accepted has not been asked.
- The 49 math records whose text differs from the paired Learning Commons item have not been read one by one.
- Whether `cacs_probe/` stays in the repo; it holds scraper test output and one saved CDE results page.
- GitHub still serves the commit that held `ccssmgraph.pdf` (20bc256) to anyone with its ID; only GitHub Support can remove it.
- What the search-all download's Main Category corresponds to (not checked).
- Whether to commit the fetched HTML pages next to each records file. (0011)
- Whether `query=a` on `/cacs/all` matches every standard in subjects other than ELA.
- `/cacs/eld` has no Part III; whether one exists in a usable form is not checked.
- Availability and licensing of Dynamic Learning Maps and Core Content Connectors (not checked).
- How end users on macOS will get the tool: installing Python and running the setup script, a packaged app, or a hosted web page. The setup scripts are for development and assume comfort with a terminal.
- Whether Python 3.13 (Debian 13's version) is acceptable on the laptop, or 3.14 should be installed there. The loader, join script, and lookup use only the standard library; `tomllib` needs 3.11 or later.
