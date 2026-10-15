Glossary for catch_the_standards

Terms as this project uses them. When a word has more than one meaning here, the entry says which form to use. Add a term here before using it with a new meaning in code, data, or decisions. The number after an entry is the decision that set it.

acquisition: first learning stage in the instructional hierarchy. The student is learning to perform the skill accurately. Stage value `acquisition`. (0009)

adaptation: fourth learning stage in the instructional hierarchy. The student modifies the skill to solve new kinds of problems. Stage value `adaptation`. (0009)

application: target type. The standard asks the student to use concepts and procedures to solve problems, often word problems or real-world problems. Value `application`. (0009)

CDE record ID: the number in a standard's URL on the CDE site, e.g. 5531 in `/cacs/id/web/5531`. Unique per record. Each ELD proficiency level is a separate record, so one ELD standard has several record IDs. Kept on every row. Distinct from identifier.

cluster: third filter level (c2) on the ELA subject page, below subject area and domain. Example: "Conventions of Standard English". (0002)

cluster alias: a mapping that treats one CDE cluster code as another. ELA cluster 3 "Conventions of Standards English" maps to cluster 2. The original code is still stored. (0003)

concept: an entry in the hand-built concepts list, e.g. "verb tense". The list itself is not decided yet. (0006)

concept tag: a link between a standard or sub-item and a concept, with a role: introduces, develops, or expects mastery. (0006)

conceptual: target type. The standard asks the student to understand an idea, e.g. what a fraction is or why an algorithm works. Value `conceptual`. (0009)

curated data: files in `data/curated/` holding the owner's reviewed judgments: concepts, concept tags, edges. Rows are added, never overwritten or reordered. (0007)

domain: second filter level (c1) on the ELA subject page, e.g. Language. (0002)

dual-identified: a student with an IEP who is also an English learner. (0009)

edge: a directed relationship from one standard to another, stored as a row in `edges` with type, weight, source, and reviewed. (0006)

EL: English learner, as identified by the student's district.

ELD proficiency level: Emerging (Em), Expanding (Ex), or Bridging (Br). It is the last part of an ELD identifier, and the same codes are used in guidance scope. (0005, 0009)

fact_fluency: target type. Fast, accurate recall of basic facts, e.g. 2.OA.2, 3.OA.7. Not the same as the learning stage `fluency`. (0009)

fluency (stage): second learning stage in the instructional hierarchy. The student builds an accurate skill into a fast one. Applies to any skill, conceptual ones included. Stage value `fluency`. Don't write "fluency" alone where the meaning could be a target type; use `fact_fluency`, `procedural_fluency`, or "stage fluency". (0009)

generalization: third learning stage in the instructional hierarchy. The student uses the skill in new settings and materials. Stage value `generalization`. (0009)

grade code: integer for a grade. 0 = TK & K, 1–12 = grades 1–12. The site shows kindergarten as "K" on results pages and "TK & K" in the dropdown; both are 0. (0002, 0004)

grade_min, grade_max: the lowest and highest grade codes a standard covers. Equal for single-grade standards. (0004)

grade range: a standard covering more than one grade, e.g. 9–10. The results pages write it with an en dash (–); identifiers use a hyphen (L.9-10.1). (0004)

guidance record: a row describing a teaching method or practice, with its source, the scope the source states, the evidence strength the source states, and reviewed. Shown when its scope matches the teacher's situation, never ranked. (0009)

identifier: CDE's standard code, e.g. L.3.1e, RF.K.2, ELD.PI.K.12b.Em. Parsed into parts and stored as columns. Distinct from CDE record ID. (0005)

instructional hierarchy: the four learning stages (acquisition, fluency, generalization, adaptation) from Haring and Eaton (1978). Used for the learning stage dimension. (0009)

learning stage: where a student is with a particular concept, as a position in the instructional hierarchy. Belongs to the student and concept together, not to a standard. The teacher gives it at query time; the database does not store it. (0009)

population: optional scope fields describing students: tier or setting, grade band or age, EL status, ELD proficiency level, dual identification. Given at query time and not stored for students. (0009)

prerequisite: an edge type meaning the "from" standard is learned before the "to" standard. Directed. Similarity alone never creates one. (0006)

procedural_fluency: target type. Carrying out algorithms accurately and efficiently, e.g. 4.NBT.4, 5.NBT.5. Term from National Research Council, Adding It Up (2001), where it also includes flexibility in choosing procedures. (0009)

progression: the sequence of standards with the same strand and number across grades, ordered by grade_min, e.g. L.K.1 through L.11-12.1. Generated by the loader as structural edges. (0005)

reviewed: column on curated and guidance rows. 0 = machine-generated or not yet checked. 1 = confirmed by the owner. Only the owner sets 1. (0006, 0007)

SAI: specialized academic instruction, the special education service the tool is mainly for.

scope: what a guidance record applies to, on three dimensions: target type, learning stage, population. Recorded exactly as the source states it, never widened. (0009)

source (column): on an edge or guidance row, where the row came from, e.g. structural, CDE text, embedding suggestion, or a citation. Not the same as "data source", which means the CDE download a standard came from. (0006, 0009)

sub-item: a lettered part of a standard, e.g. the e in L.3.1e. Stored as its own row linked to the parent. An asterisk marks sub-items CDE flags as needing continued attention in higher grades. (0005)

subject area: first filter level (c0) on the ELA subject page, e.g. "English Language Arts (6–12)". (0002)

target type: the kind of knowledge a standard or sub-item asks for: `fact_fluency`, `procedural_fluency`, `conceptual`, `application`. A property of the standard. Suggested by script from the standard's wording with reviewed=0, then confirmed by the owner. A standard can have more than one. (0009)

Tier 2, Tier 3: intervention levels in a multi-tiered system of supports. Tier 2 is targeted small-group support. Tier 3 is intensive, often individual, support. Many research guides limit their scope to these tiers.
