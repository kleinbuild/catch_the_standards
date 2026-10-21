0004 Store grades as grade_min and grade_max

Status: accepted, 2026-10-08; amended 2026-10-20 by 0011 and 0012

Each standard gets two integer columns, `grade_min` and `grade_max`, using the site's codes (0 = TK & K, 1–12). Single-grade standards get the same value in both. "Which standards apply at grade 10" is `WHERE 10 BETWEEN grade_min AND grade_max`.

Some standards cover a range, not a grade. High school ELA results show "Grade Range: 9–10" and "Grade Range: 11–12" in place of "Grade:", with identifiers L.9-10.1 and L.11-12.1. Computer Science shows "Grade Range: K–2" for K-2.AP.10.

The range separator on the results pages is an en dash (–), not a hyphen, while identifiers use a hyphen (9-10). Check how the CSV writes the grade column before parsing it, and accept both characters.

Kindergarten appears as "K" on results pages and as "TK & K" (code 0) in the grade dropdown. Map both to 0.

Amendment, 2026-10-20 (0011, 0012)

Identifiers do not all use a hyphen. The HTML writes the grade band with an en dash in RH, RST, and WHST identifiers and in high school ELD identifiers (RH.6–8.1, ELD.PI.9–10.1.Br). Other ELA identifiers use a hyphen (L.9-10.1). The CSV export writes hyphens. Each row stores the identifier as written and a copy with every dash as a hyphen (0012).

Grades are read from the scraped Grade or Grade Range field (0011), so the CSV's grade column no longer needs parsing. The CSV's Min Grade and Max Grade columns only split the same range, and no grade differed between the CSV and the scrape in any of math, ELA, or ELD.
