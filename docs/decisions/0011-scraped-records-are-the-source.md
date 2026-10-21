0011 Scraped HTML records are the source of standards; the dl=1 CSV is a cross-check

Status: proposed, 2026-10-20. Amends 0001.

Load standards from `data/raw/<subject>_records_<date>.csv`, written by `scripts/scrape_cacs_records.py` from the subject pages' HTML results, one row per CDE record. Keep the dl=1 CSVs in `data/raw/` as well, and run `scripts/match_csv_to_records.py` after every new scrape or download. If any CSV row or any scraped record is left unpaired, the new scrape is not loaded until the cause is found.

This keeps 0001's choice of the subject pages over `/cacs/all`. It changes which output of those pages is loaded: the HTML results (`dl=0`) instead of the CSV export (`dl=1`).

Every table in the database identifies a standard by its CDE record ID, in every subject, including subjects where identifiers happen to be unique. Edges, concept tags, and curated rows refer to record IDs (see 0006).

The scrape requests `https://www2.cde.ca.gov/cacs/<subject>?mingrade=0&maxgrade=12&order=0&page=<n>&perpage=100&dl=0`, with `page` counting up from 0 until the site's total is reached. `maxgrade=12` is required, because the default of 0 returns kindergarten only (0002). With `dl=0`, `page` and `perpage` matter again, unlike with `dl=1` (0002). The scraper waits 1 second between pages.

The records file has these columns: `record_id` (the number in `/cacs/id/web/<n>`), `url` (the full record URL), `identifier` (as written on the page), one column per field label the page shows for that subject, one `text_<Section>` column per text section, and `page` (the results page the record came from, kept for checking the scrape). It is written as UTF-8 with no byte-order mark. Excel on Windows may show the symbols wrongly if the file is opened directly; the file itself is correct.

The CSV has no record IDs, and identifiers are not unique in every subject. ELA identifiers are unique: 568 rows, 568 identifiers (0001). The math CSV has 734 rows and 497 unique identifiers; 151 appear more than once. High school standards are listed once per course: A-CED.1 has rows for Algebra I, Math I, Math II, Algebra II, and Math III, and the HTML gives Algebra I record 558 and Math I record 721. Identifier plus course is not unique either: Calculus.16.0 has two Calculus rows with different standards (definite integrals in applied problems; computing integrals by hand). Only the record ID is unique, and only the HTML has it.

The CSV loses symbols. The export is cp1252 and writes "?" for characters cp1252 lacks. F-BF.4.a in Algebra II and Math III reads `(x ? 1)/(x ? 1) for x ? 1`; the original is `(x + 1)/(x − 1) for x ≠ 1`. A request with `Accept-Charset: utf-8` returned no UTF-8 bytes for − or ≠. The HTML is served as `text/html; charset=utf-8`, and the full math scrape contains 9 minus signs and 3 not-equal signs. The only "?" between math terms in the scrape is a real question in 1.OA.7. Subtraction is written two ways, and only one of them survives the export; see 0012.

The scrape holds everything the CSV does. `match_csv_to_records.py` paired every CSV row with exactly one scraped record, on identifier (plus Discipline for math) and text, after converting the scraped text the way the cp1252 export does. Identifiers were compared with every dash as a hyphen (0012). An exact match has identical text. A loose match differs only in dashes, quote style, "?", or spacing. Results: math 734 of 734 (660 exact, 74 loose), ELA 568 of 568 (424 exact, 144 loose), ELD 771 of 771 (716 exact, 55 loose). No grade differed. No record appeared on more than one results page, and each scrape's record count matched the site's "Showing X of Y" total. The CSV's Min Grade and Max Grade only split the grade range, which the loader computes (0004).

The HTML separates the text into sections; the CSV has one Description column. Math has Cluster, Standard, and Footnote sections; ELA has Standard and Footnote; ELD has Standard.

Field labels differ by subject, and the scraper reads them from the page. Math K–8: Grade, Domain. Math high school: Grade Range, Discipline, Conceptual Category. ELA: Grade or Grade Range, Subject Area, Domain, Cluster. ELD: Grade or Grade Range, Critical Principle, Cluster, Proficiency Level, Content Strand. The same name can mean different things. In ELA, Cluster is a short label field (the c2 filter level, 0002). In math, the cluster statement with its course note is the `text_Cluster` section. The loader maps columns per subject.

Effects on earlier decisions, recorded as amendments in each: 0001 (loading source; `compare_cacs.py` is valid for ELA only), 0003 (cluster arrives as a label, not a code), 0004 (grades come from the scraped field), 0005 (parse the records file; high school math progressions), 0006 (edges use record IDs), 0007 (the records file is script output, not a download).

Not decided or not yet checked:
- Whether to commit the fetched HTML pages next to the records file. Without them, a scraper bug found later can only be fixed by scraping again, and the site may have changed by then.
- Whether `match_csv_to_records.py` also confirms that no scraped record was paired with two CSV rows. Calculus.16.0 is where a loose match could pair both of its CSV rows with one record. Equal totals alone do not rule that out.
- `match_csv_to_records.py` is not in the repository yet (checked 2026-10-20).
