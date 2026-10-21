0005 Parse identifiers into parts; build progressions from them

Status: accepted in principle, 2026-10-08; amended 2026-10-20 by 0011 and 0012.

Split each standard identifier into its parts and store them as columns. Generate vertical progression edges from the parts instead of from cluster names.

ELA identifiers are strand.grade.number, with grade as K, a number, or a range: RF.K.1, L.6.1, L.9-10.2, L.11-12.1. The same strand and number carries the same skill strand across grades. Every L.x.1 from K to 11-12 opens with the same grammar-and-usage stem, and every L.x.2 with the capitalization-punctuation-spelling stem. So "same strand, same number, ordered by grade_min" gives the progression for that standard.

Lettered sub-items (a, b, c...) carry the finer skill progression and become their own rows linked to the parent. Example from the L.1 sequence: verb tense runs L.1.1e (past/present/future), L.3.1e (simple tenses), L.4.1b (progressive), L.5.1b–d (perfect, sequences, shifts), L.8.1b–d (voice and mood). Asterisked sub-items are flagged by CDE as needing continued attention in higher grades (footnote from grade 3 on); keep the asterisk as a column.

ELD identifiers have more parts and a proficiency level: ELD.PI.K.12b.Em is Part I, grade K, standard 12b, level Emerging. The same standard exists as separate records per level, each with its own CDE ID: ELD.PI.K.12b.Em is 7020, ELD.PI.K.12b.Ex is 7025. Store part, grade, number, letter, and level (Em, Ex, Br) as columns, so a query can pick the band matching a student's ELD level.

California additions end with "CA" in the text (e.g. RF.K.2 f, L.1.1d). Keep that as a flag.

Still needed: the CSV header row and 2–3 rows from an ELA download and an ELD download, to confirm which column holds the identifier and how grade and sub-items are written.

Amendment, 2026-10-20 (0011, 0012)

Parse the scraped records file, not the CSV. Its columns answer the "Still needed" item above: the identifier is in `identifier`, the grade is in the Grade or Grade Range field, and the text is in the `text_` columns. Parse `identifier_norm`, which has every dash as a hyphen (0012). Each parsed row is one CDE record and is keyed by its record ID.

The progression rule above ("same strand, same number, ordered by grade_min") works where the grade is part of the identifier: ELA, and ELD. It does not fit high school math. A-CED.1 has no grade in it, and the same identifier is a separate record in each course (Algebra I 558, Math I 721). Calculus.16.0 is two different standards in the same course, which only the record ID tells apart. A progression rule for high school math is not decided.

Math sub-items have their own identifiers and records (F-BF.4.a). Whether ELA and ELD sub-items are separate records has not been checked.

ELA footnotes arrive in a separate `text_Footnote` section. Check whether the asterisk footnote described above is there before deciding where the asterisk column comes from.

`/cacs/eld` holds ELD Part I (507 records) and Part II (264), and no Part III. ELD parsing, progressions, and ELD-to-ELA bridge edges cover Parts I and II until a Part III source is found.
