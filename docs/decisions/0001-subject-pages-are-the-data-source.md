0001 Subject pages are the data source; /cacs/all is for search only

Status: accepted, 2026-10-12; amended 2026-10-20 by 0011

Use the per-subject download (`/cacs/<subject>?...&dl=1`) to load standards. Use `/cacs/all` only for cross-subject text search.

The two downloads contain the same ELA standards. `compare_cacs.py --fetch ela` returned 568 rows from each, 568 identifiers in both, 0 in only one, and no differing values in any shared column.

Only the subject download has the hierarchy. The subject CSV has 9 columns including Subject Area, Domain, and Cluster. The search-all CSV has 7 columns and replaces those three with a single Main Category. Grouping and sequencing need all three levels.

Both endpoints return real CSV files. Response headers were `text/csv` with `attachment; filename=CA_English_Language_Arts_Standards.csv` (subject) and `filename=CA_Content_Standards.csv` (search-all).

`dl=1` exports the full result set, not one page. Both downloads returned 568 rows with `perpage=100` in the URL. An earlier check on `c0=1&c1=2&maxgrade=5` also matched the "Showing X of Y" count on the page.

`/cacs/all` requires search text. The page's script blocks an empty query and the input is marked `data-val-required`. The search matches substrings: "add" matched "address" and "Additionally" (437 results). `query=a` happened to return every ELA standard; that has not been checked for other subjects.

`/cacs/all` is still useful for: finding cross-subject references in standard text, and CTE, which it splits into Anchors (carea 11) and Pathways (carea 12).

Amendment, 2026-10-20 (0011)

Standards are now loaded from the subject pages' HTML results (`dl=0`), scraped into `data/raw/<subject>_records_<date>.csv`. The `dl=1` CSV is kept as a cross-check. The choice of subject pages over `/cacs/all` stands.

The result above of 568 identifiers in both and 0 in only one holds because ELA identifiers are unique. Math identifiers are not: 734 rows, 497 identifiers. `compare_cacs.py` keys rows by identifier and keeps only the last row for each, so its counts are wrong for any subject with repeated identifiers. Use it for ELA only. `match_csv_to_records.py` (0011) pairs every CSV row with a scraped record instead.
