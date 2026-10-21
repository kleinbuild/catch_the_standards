0012 Store identifiers as written plus a hyphen-normalized copy; treat minus sign, en dash, and hyphen as equal when searching text

Status: proposed, 2026-10-20. Amends 0004.

Each standard row keeps `identifier` exactly as CDE writes it and adds `identifier_norm`, the same string with every en dash (U+2013) replaced by a hyphen. Joins, progressions (0005), matching against the CSV (0011), and parsing citations in standard text (0006) use `identifier_norm`. Display and links back to the site use `identifier`. Only dashes are normalized. Any other difference between two identifiers is treated as real until checked.

Identifiers use mixed dashes. The HTML writes the grade band with an en dash in RH, RST, and WHST identifiers and in high school ELD identifiers (RH.6–8.1, ELD.PI.9–10.1.Br). Other ELA identifiers use a hyphen (L.9-10.1). The CSV export writes hyphens. 90 ELA rows and 150 ELD rows went unmatched until identifiers were compared with all dashes as hyphens. This corrects 0004, which says identifiers use a hyphen.

Standard text is stored as written. For searching, the loader also keeps a form of each text section with the minus sign (U+2212) and en dash (U+2013) replaced by a hyphen, and search runs on that form. Subtraction is written both ways in the HTML: the minus sign in F-IF.3 (`f(n − 1)`) and the en dash in A-REI.4.a (`(x – p)^2`). A search typed with a keyboard hyphen would otherwise miss both.

The two characters also explain why only some subtraction became "?" in the CSV export (0011). cp1252 has the en dash and lacks the minus sign, so the en dash survives the export and the minus sign does not.

Grade ranges in the scraped Grade Range field use an en dash ("9–10"). The grade parser accepts an en dash or a hyphen, as 0004 already says.

Not decided: whether other dash-like characters (em dash U+2014, non-breaking hyphen U+2011) are normalized too. None have been looked for.
