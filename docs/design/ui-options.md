Interface options: first thoughts before prototyping

Status: notes for discussion, 2026-11-14. Nothing here is decided. Written by Claude at the owner's request, to start the next working session from.

What the data can show today

Everything below is already in `data/build/standards.db` and printed by `python src/lookup.py`. An interface is a way of showing these, so the list is the raw material.

- A standard: its text, its lettered sub-items (ELA), its parent standard (math), a link to its page on the CDE site.
- What it builds on, walking back by steps: the same strand a grade earlier (ELA, ELD), the proficiency level below (ELD), the standards Learning Commons says build towards it (math, K–12).
- For an ELD standard, the ELA standards listed against it; for an ELA standard, the ELD standards that list it.
- Learning components: the teachable pieces of a standard. Math K–12, ELA grades K–2 only.
- For every link, where it came from and whether the owner has reviewed it. On 2026-11-14 none is reviewed.

What the data cannot show yet, so a prototype should not promise it: prerequisites across ELA strands (only the same strand a grade earlier exists), ELA components above grade 2, teaching-method guidance (0009 is proposed, no data), anything about a student.

Who uses it and when

- A special education teacher planning reteaching: starts from a grade-level standard the student is missing, wants the earlier or prerequisite standards to check and teach.
- The same teacher writing an IEP goal: wants a prerequisite standard at the student's actual level and wording specific enough to measure. Learning components may be the right grain for that.
- A general education teacher is asked by a special education teacher to provide IEP input for progress and present levels of performance. The teacher may have only standard codes for the student, but wants to help more. They can also share informal observations with the special education teacher such as 'Timmy has difficulty with adding 3 digit numbers, with carrying over, and with regrouping.' Either the general education or special education teacher should be able to use this tool to both survey earlier prerequisite or prior related grade level standards to those known through assessment, and also keyword or keyphrase search for tags of skills/concepts (possibly filtered through broadly related standards, or expanded to a broader set of standards- maybe with toggles for searching only directly related/prior standards, or including more broadly related standards, or going to global all standards search, or expanding further to any included non-academic-standards related skills or knowledge in the database such as life skills, prevocational skills, social skills, etc., or building blocks of basic skills and foundational skills).
- For a dual-identified student: the teacher needs to write ELD goals and may need to spiral down to directly related prior grade level standards or write a goal focused on foundational skills that support the student making progress toward a grade level goal.

Questions for the owner that change the design

1. Where does a teacher start: from a standard code they already know, from a grade and subject they browse, or from a description of what the student cannot do? The third needs text search to be the front door.

Answer: All of these need to be available, because teachers have different levels and types of information available to them - sometimes standards only, sometimes grade/subject only, sometimes informal skill observation only, or some mix of all three kinds. They need to be able to start from any of these and combine/filter options to refine their search.

1. When is it open: alone at a desk while planning, or on a screen in an IEP meeting with a parent present? A meeting view needs plain language and less on screen.

Answer: This is a planning and preparation tool, not an execution/presentation tool. It can be used by one teacher alone, or by a group of teachers and education / student support professionals sitting around a table to collaborate. It could potentially be used in a meeting collaboratively with a parent and education professionals, but this would be only in the rare instances where parents want to be directly involved in shaping student goals beyond what is normal in the parent-school collaboration process. For such a parent, a teacher could also use the tool to show how the foundational instructional methods and materials they are using are related to grade level standards and skills, if questioned about using instructional materials for supplemental instruction that are below grade level. This could also be helpful for teachers in communicating with administrators about how their intervention and specialized / supplemental instruction and reteaching is related to grade level standards and skills.

1. What does the teacher carry away: a list to print, text to paste into the IEP system, a saved set to come back to? Which IEP system, if pasting matters (SEIS?).

A teacher might come away with a standard, a portion of a standard, a focused set of skills. If the data could be secured it might be helpful if they can have something like a chain of thought or custody of data even, showing- the teacher entered certain data, the program provided certain insights, and the teacher is using the data and insights to tailor the instructional program to the specific needs of a specific student. IEP systems are unknown, common in the LA area is Welligent, and in a larger part of California SEIS, and there may be others.

2 . Phone, Chromebook, or laptop? Most end users are on Mac (CLAUDE.md); whether school-issued devices allow installing software decides a lot.

Teachers are always on the go so if there is a way to access this on their phones, even in a more lightweight or streamlined version, that could be of benefit. Laptops, mostly macs, are common, and about 50% of the time users are not permitted to install any apps on district devices. That is kind of the rub of it.

1. How should an unreviewed link look next to a reviewed one? Hidden until reviewed, shown as "suggested", or shown the same with the source named.

Shown with source named and confidence measure. Besides the LLM confidence of match measure, human review can also include an optional confidence metric (simple and qualitative)

1. High school math: does the teacher pick the student's course first (Algebra I or Math I), so only that pathway's copies appear?

Yes, the teacher should likely pick the course first. However, if the course is unknown, there should be an option perhaps that searches all, with a disclaimer or explanation of what is happening and why.

How teachers would get it

Four ways, with what each costs.

A. A web page with the database inside it. The page and the data are plain files; the browser does the searching. Nothing is installed, it works on Mac, Chromebook and phone, and nothing a teacher types leaves the device because there is no server. It can be hosted free on GitHub Pages from this repo, and saved for offline use. The database is 5.3 MB as built on 2026-11-14, which a browser loads in a second or two; it can be shipped as the SQLite file read by sql.js (SQLite compiled to run in a browser) or exported to JSON. This also fits the owner's idea of each user holding a local copy of the data.

B. A program run from Python on the teacher's machine. This is what exists now. It needs Python installed and a terminal, which rules it out for most teachers. It is the fastest way to prototype, and useful to the owner.

C. A packaged desktop app. One download, no Python. On macOS an app that is not signed with a paid Apple developer account ($99 a year) is blocked by default, and each update is a new download.

D. A hosted web application with a server and accounts. It would allow saved work across devices, but brings hosting cost, sign-in, and responsibility for whatever teachers store. Since 0009 keeps student information out of the database on purpose, the main reason for a server is absent.

Claude's recommendation is A, prototyped first as a single HTML file. It reaches every device with no install, has no running cost, and keeps the no-student-data rule true by construction. Saved lists, if wanted, can live in the browser's own storage on that device. The cost is that the interface is written in HTML, CSS and JavaScript, not Python; Python stays for building the data.

How the prerequisite view could look

Three ways to draw "what this builds on", which is the heart of the tool.

- A ladder: the chosen standard at the top, earlier standards below it grouped by grade, each as a card with its text, the kind of link, and its source. This is what `lookup.py` prints. It reads top to bottom, prints well, and works with a screen reader.
- A map: standards as boxes joined by arrows, like the Student Achievement Partners coherence map. It shows how routes join, and it looks impressive. It gets crowded fast: 4.NF.3.a has eight standards one step back, and maps are hard to print and hard to use without a mouse.
- A table: one row per earlier standard, columns for grade, link, source. Dense and sortable, good for pasting into a document, poor for seeing structure.

Claude would prototype the ladder first and add the map only if the owner finds the ladder hides something that matters.

Screens a first prototype needs

1. Find a standard: a search box that takes a code or words, with subject and grade filters. High school math asks for the course.
2. The standard: its text and sub-items; the ladder beneath it with a control for how far back to go; a side panel for learning components; for ELD and ELA, the bridge with a proficiency-level choice (Emerging, Expanding, Bridging).
3. A collected list: standards and components the teacher has picked, in a form that prints on one page and copies as plain text.

Things already known to be awkward

- Fan-out. Some math standards have many standards one step back, and each of those has more. The view needs a depth limit and a way to open one branch at a time.
- Long bridge lists. An ELD standard lists between 3 and 43 ELA standards. A list of 43 needs grouping by strand.
- Course copies. A-CED.1 is five records. Without a course choice the teacher sees five near-identical results.
- Parent standards. 4.NF.3 has no CDE record; the interface has to say so without making it look like an error.
- Trust. Every link is unreviewed today. If the interface hides unreviewed links it shows nothing; if it shows them plainly it may claim more than is known.
- Accessibility. Teachers and students with disabilities are the audience; keyboard use, screen readers, contrast, and print all need to work from the first version.

A possible first step for the next session

The owner answers the six questions above, in whatever detail comes easily. Claude then builds one HTML file with real data for three standards (L.5.1, 4.NF.3.a, ELD.PI.4.6a.Ex), showing the standard screen in two layouts side by side, so the owner can react to something concrete. That file opens by double-click and needs no server. A script to export the whole database for the page comes after a layout is chosen.
