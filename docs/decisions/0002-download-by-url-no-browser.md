0002 Download with plain GET requests; no browser automation

Status: accepted, 2026-10-08

Build download URLs directly and fetch them with `requests`. Playwright is not needed.

The page's download button only sets a hidden field and resubmits a GET form. Its script is `$("#dl").val(1); $("#CriteriaForm").submit();`, and `CriteriaForm` is `method="get"` with every filter as a hidden input. So the download URL is the results URL with `dl=1`.

This was confirmed on the owner's machine. Pasting the `dl=1` URL into a browser and running the Python builder sketch both downloaded the same CSV. No cookie or session was needed.

URL parameters, from the form's hidden inputs and the dropdown scripts:
- `c0`, `c1`, `c2`: filter levels. On ELA these are Subject Area, Domain, Cluster. Leave out unused levels. Several values go comma-separated (`c1=2,3`); the page's own "add criterion" links use `c0=1%2C2`.
- `mingrade`, `maxgrade`: 0 = TK & K, 1–12 = grades. Both default to 0, which returns kindergarten only. The first example URL used `maxgrade=0` and returned 4 standards, all RF.K.x, though the RF domain covers K–5.
- `order`: sort order. Codes differ by page. ELA: 0 Grade Range, 1 Subject Area, 2 Domain, 3 Cluster, 5 Standard Identifier. /cacs/all: 1 Grade Range, 2 Content Area, 3 Standard Identifier, 4 Category.
- `page`, `perpage`: 10, 25, or 100. Irrelevant with `dl=1` (see 0001).
- `dl`: 0 = HTML page, 1 = file download.
- `/cacs/all` only: `query` (required), `carea` (content area). Its defaults differ: `perpage=10`, `maxgrade=12`.

The c0/c1/c2 code numbers belong to each subject page. `scripts/cacs_codes.py` reads them from each page's dropdowns and writes `docs/reference/`. A selected criterion disappears from its dropdown and shows only as a "remove" link, so the script reads selected values from the hidden inputs.

`/cacs/all` carea codes: 0 All, 1 Computer Science, 2 Mathematics, 3 Health, 4 History–Social Science, 5 Arts, 6 World Languages, 7 ELA, 8 School Library, 9 PE, 10 ELD, 11 CTE Anchors, 12 CTE Pathways, 13 Science.

`/cacs/all` loads results by form submission, not a JSON API. Its source has no fetch or ajax calls. The page advertises a mobile app (`gov.ca.cde.CACSMobile`); whether that has an API was not investigated.
