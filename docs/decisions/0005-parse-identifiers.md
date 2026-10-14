0005 Parse identifiers into parts; build progressions from them

Status: accepted in principle, 2026-10-08. Parsing rules wait on real CSV rows.

Split each standard identifier into its parts and store them as columns. Generate vertical progression edges from the parts instead of from cluster names.

ELA identifiers are strand.grade.number, with grade as K, a number, or a range: RF.K.1, L.6.1, L.9-10.2, L.11-12.1. The same strand and number carries the same skill strand across grades. Every L.x.1 from K to 11-12 opens with the same grammar-and-usage stem, and every L.x.2 with the capitalization-punctuation-spelling stem. So "same strand, same number, ordered by grade_min" gives the progression for that standard.

Lettered sub-items (a, b, c...) carry the finer skill progression and become their own rows linked to the parent. Example from the L.1 sequence: verb tense runs L.1.1e (past/present/future), L.3.1e (simple tenses), L.4.1b (progressive), L.5.1b–d (perfect, sequences, shifts), L.8.1b–d (voice and mood). Asterisked sub-items are flagged by CDE as needing continued attention in higher grades (footnote from grade 3 on); keep the asterisk as a column.

ELD identifiers have more parts and a proficiency level: ELD.PI.K.12b.Em is Part I, grade K, standard 12b, level Emerging. The same standard exists as separate records per level, each with its own CDE ID: ELD.PI.K.12b.Em is 7020, ELD.PI.K.12b.Ex is 7025. Store part, grade, number, letter, and level (Em, Ex, Br) as columns, so a query can pick the band matching a student's ELD level.

California additions end with "CA" in the text (e.g. RF.K.2 f, L.1.1d). Keep that as a flag.

Still needed: the CSV header row and 2–3 rows from an ELA download and an ELD download, to confirm which column holds the identifier and how grade and sub-items are written.
