Glossary for catch_the_standards

Terms as this project uses them. When a word has more than one meaning here, the entry says which form to use. Add a term here before using it with a new meaning in code, data, or decisions. The number after an entry is the decision that set it.

Start here if you are new: a standard on the CDE site can appear as more than one record. Each ELD proficiency level is its own record, and each high school math course lists its own copy of a shared standard. The project identifies everything by CDE record ID. The identifier (L.3.1e, A-CED.1) is what teachers read, but it is not always unique. See record, identifier, and CDE record ID.

/cacs/all: the CDE search page across all subjects. Used for cross-subject text search, not for loading standards. Requires search text. Its content area filter is `carea`. (0001, 0002)

acquisition: first learning stage in the instructional hierarchy. The student is learning to perform the skill accurately. Stage value `acquisition`. (0009)

adaptation: fourth learning stage in the instructional hierarchy. The student modifies the skill to solve new kinds of problems. Stage value `adaptation`. (0009)

application: target type. The standard asks the student to use concepts and procedures to solve problems, often word problems or real-world problems. Value `application`. (0009)

build: the step that deletes and recreates `data/build/standards.db` from the files in `data/raw/` and `data/curated/`, run by `src/load.py`. The database is build output and is never edited by hand or committed. (0007, 0010)

CA addition: a standard or sub-item California added to the Common Core, marked by "CA" at the end of its text. Kept as a flag. (0005)

carea: content area code used only on `/cacs/all` (ELA 7, ELD 10, Math 2, Science 13, CTE 11 and 12). Not the same numbers as the c0/c1/c2 filter codes on subject pages. (0002)

CDE: California Department of Education. Its standards site is www2.cde.ca.gov/cacs.

CDE record ID: the number in a record's URL on the CDE site, e.g. 5531 in `/cacs/id/web/5531`. Unique per record, and the key for every standard in the database, in every subject. Only the HTML results pages show it; the dl=1 CSV does not. Stored as `record_id`. Distinct from identifier. (0011)

cluster: has two meanings depending on subject. In ELA, a short label and the third filter level (c2) below subject area and domain, e.g. "Conventions of Standard English" (0002). In math, the cluster statement with its course note, stored as the text section `text_Cluster` (0011). ELD records also have a Cluster field. Say which subject you mean.

cluster alias: a mapping that treats one CDE cluster code as another. ELA cluster 3 "Conventions of Standards English" maps to cluster 2. The original code is still stored. The scrape gives the label; the loader looks up the code in `docs/reference/codes.csv`. (0003, 0011)

concept: an entry in the hand-built concepts list, e.g. "verb tense". The list itself is not decided yet. (0006)

concept tag: a link between a standard or sub-item and a concept, with a role: introduces, develops, or expects mastery. Refers to the standard by record ID. (0006, 0011)

conceptual: target type. The standard asks the student to understand an idea, e.g. what a fraction is or why an algorithm works. Value `conceptual`. (0009)

Conceptual Category: a field label on high school math records, the category the standard belongs to across courses. (0011)

Content Strand: a field label on ELD records. Its values have not been listed here yet. (0011)

course: in prose, a high school math course such as Algebra I or Math I. The site and the data call it Discipline. A shared high school standard appears once per course, each with its own record ID. (0011)

cp1252: the Windows Western European text encoding. The dl=1 CSV export uses it, and it has no minus sign or not-equal sign, so those become "?". Also the default encoding Python uses for files on Windows unless told otherwise, which is why scripts open files with `encoding="utf-8"` or `encoding="cp1252"` named. (0011)

Critical Principle: a field label on ELD records. Its values have not been listed here yet. (0011)

cross-check: comparing the dl=1 CSV with the scraped records file, done by `scripts/match_csv_to_records.py` after each new scrape or download. Every CSV row and every record must pair, or the new scrape is not loaded. (0011)

curated data: files in `data/curated/` holding the owner's reviewed judgments: concepts, concept tags, edges. Rows are added, never overwritten or reordered. (0007)

dash: three characters matter here. The hyphen (-, U+002D) is the keyboard character. The en dash (–, U+2013) is used for grade ranges on the site, in some identifiers, and for some subtraction. The minus sign (−, U+2212) is used for other subtraction. Identifiers and search text treat all three as the same; stored text keeps whichever CDE used. (0012)

data source: where a standard's row came from: the scraped records file for that subject. Not the same as the source column on edge and guidance rows. (0011)

Discipline: the field label for a high school math course on the site and in the CSV. See course. (0011)

dl=0, dl=1: URL parameter on CDE results pages. `dl=0` returns the HTML results page, which is what the scraper reads. `dl=1` returns the whole result set as one CSV file, kept as a cross-check. (0002, 0011)

domain: second filter level (c1) on the ELA subject page, e.g. Language (0002). Math K–8 records also have a Domain field. (0011)

dual-identified: a student with an IEP who is also an English learner. (0009)

edge: a directed relationship from one standard to another, stored as a row in `edges` with type, weight, source, and reviewed. `from` and `to` are CDE record IDs. (0006, 0011)

EL: English learner, as identified by the student's district.

ELD: English Language Development, the California standards for English learners. Kept apart from the ELA standards and linked to them by bridge edges.

ELD Part I, II, III: the three parts of the CA ELD Standards: Part I Interacting in Meaningful Ways, Part II Learning About How English Works, Part III Using Foundational Literacy Skills. The part is the second piece of the identifier (PI in ELD.PI.K.12b.Em). `/cacs/eld` has Parts I and II only. (0005, 0011)

ELD proficiency level: Emerging (Em), Expanding (Ex), or Bridging (Br). It is the last part of an ELD identifier, each level is a separate record, and the same codes are used in guidance scope. Shown on records as the Proficiency Level field. (0005, 0009, 0011)

exact match, loose match: results from the cross-check. An exact match has identical text. A loose match differs only in dashes, quote style, "?", or spacing. Identifiers are compared dash-normalized in both. (0011, 0012)

fact_fluency: target type. Fast, accurate recall of basic facts, e.g. 2.OA.2, 3.OA.7. Not the same as the learning stage `fluency`. (0009)

field label: a labeled value shown on each record of an HTML results page, e.g. Grade, Domain, Discipline. Each label becomes one column in the records file. Labels differ by subject. Compare text section. (0011)

filter code: the numbers used for the c0, c1, c2 filter levels on a subject page. They belong to that subject page and are not shared across subjects. Listed in `docs/reference/codes.csv` by `scripts/cacs_codes.py`. (0002)

fluency (stage): second learning stage in the instructional hierarchy. The student builds an accurate skill into a fast one. Applies to any skill, conceptual ones included. Stage value `fluency`. Don't write "fluency" alone where the meaning could be a target type; use `fact_fluency`, `procedural_fluency`, or "stage fluency". (0009)

generalization: third learning stage in the instructional hierarchy. The student uses the skill in new settings and materials. Stage value `generalization`. (0009)

grade code: integer for a grade. 0 = TK & K, 1–12 = grades 1–12. The site shows kindergarten as "K" on results pages and "TK & K" in the dropdown; both are 0. (0002, 0004)

grade_min, grade_max: the lowest and highest grade codes a standard covers. Equal for single-grade standards. Computed by the loader from the Grade or Grade Range field. (0004, 0011)

grade range: a standard covering more than one grade, e.g. 9–10. The Grade Range field on results pages uses an en dash. Identifiers write the grade band with an en dash in RH, RST, WHST, and high school ELD (RH.6–8.1, ELD.PI.9–10.1.Br) and with a hyphen in other ELA identifiers (L.9-10.1). (0004, 0012)

guidance record: a row describing a teaching method or practice, with its source, the scope the source states, the evidence strength the source states, and reviewed. Shown when its scope matches the teacher's situation, never ranked. (0009)

identifier: CDE's standard code, e.g. L.3.1e, RF.K.2, ELD.PI.K.12b.Em, A-CED.1. Stored exactly as written. Parsed into parts and stored as columns. Not always unique: in math, one identifier can be several records, one per course, and Calculus.16.0 is two different standards in one course. ELA identifiers are unique. Use CDE record ID to point at one standard. (0005, 0011)

identifier_norm: the identifier with every dash as a hyphen. Used for joins, progressions, matching, and citation parsing; never shown to teachers in place of the identifier. (0012)

instructional hierarchy: the four learning stages (acquisition, fluency, generalization, adaptation) from Haring and Eaton (1978). Used for the learning stage dimension. (0009)

learning stage: where a student is with a particular concept, as a position in the instructional hierarchy. Belongs to the student and concept together, not to a standard. The teacher gives it at query time; the database does not store it. (0009)

loader: `src/load.py`, the script that runs the build. Not written yet. (0007)

population: optional scope fields describing students: tier or setting, grade band or age, EL status, ELD proficiency level, dual identification. Given at query time and not stored for students. (0009)

prerequisite: an edge type meaning the "from" standard is learned before the "to" standard. Directed. Similarity alone never creates one. (0006)

procedural_fluency: target type. Carrying out algorithms accurately and efficiently, e.g. 4.NBT.4, 5.NBT.5. Term from National Research Council, Adding It Up (2001), where it also includes flexibility in choosing procedures. (0009)

progression: the sequence of standards with the same strand and number across grades, ordered by grade_min, e.g. L.K.1 through L.11-12.1. Generated by the loader as structural edges. Works for ELA and ELD. High school math identifiers carry no grade, and their progression rule is not decided. (0005)

raw data: files in `data/raw/`, committed with a date in the name: scraped records files (UTF-8) and dl=1 CSV downloads (cp1252). Records files are script output, not downloads. (0007, 0011)

record: one entry on the CDE site, with its own page at `/cacs/id/web/<record ID>`. Usually one standard or sub-item. The same standard can be several records: one per ELD proficiency level, one per high school math course. Each row of a records file is one record. (0011)

records file: `data/raw/<subject>_records_<date>.csv`, written by `scripts/scrape_cacs_records.py`. One row per record, with record_id, url, identifier, one column per field label, one `text_<Section>` column per text section, and page. UTF-8. The source the loader reads standards from. (0011)

reviewed: column on curated and guidance rows. 0 = machine-generated or not yet checked. 1 = confirmed by the owner. Only the owner sets 1. (0006, 0007)

SAI: specialized academic instruction, the special education service the tool is mainly for.

scope: what a guidance record applies to, on three dimensions: target type, learning stage, population. Recorded exactly as the source states it, never widened. (0009)

scraper: `scripts/scrape_cacs_records.py`. Requests every HTML results page for one subject, 100 records per page, waiting 1 second between pages, and writes the records file. Runs on the owner's machine; the cloud workspace cannot reach the CDE site. (0011)

source (column): on an edge or guidance row, where the row came from, e.g. structural, CDE text, embedding suggestion, or a citation. Not the same as data source. (0006, 0009)

structural edge: an edge generated by the loader from identifier parts (same strand and number in the next grade), not from review or similarity. The most trusted edge source. (0005, 0006)

sub-item: a lettered part of a standard, e.g. the e in L.3.1e. Stored as its own row linked to the parent. An asterisk marks sub-items CDE flags as needing continued attention in higher grades. In math, sub-items are their own records (F-BF.4.a); in ELA and ELD this has not been checked. (0005)

subject area: first filter level (c0) on the ELA subject page, e.g. "English Language Arts (6–12)". (0002)

subject page: the CDE results page for one subject, `/cacs/<subject>` (e.g. `/cacs/math`, `/cacs/ela`, `/cacs/eld`). The data source for standards. Compare /cacs/all. (0001)

target type: the kind of knowledge a standard or sub-item asks for: `fact_fluency`, `procedural_fluency`, `conceptual`, `application`. A property of the standard. Suggested by script from the standard's wording with reviewed=0, then confirmed by the owner. A standard can have more than one. (0009)

text section: a named part of a record's text on the HTML results page: Cluster, Standard, or Footnote, depending on subject. Each becomes a `text_<Section>` column in the records file. The dl=1 CSV joins them into one Description column. Compare field label. (0011)

Tier 2, Tier 3: intervention levels in a multi-tiered system of supports. Tier 2 is targeted small-group support. Tier 3 is intensive, often individual, support. Many research guides limit their scope to these tiers.

UTF-8: the text encoding of the CDE HTML pages and of every file this project writes. It holds every character, including − and ≠. (0011)
