# CACS URL reference
Generated 2026-10-12 by cacs_codes.py from https://www2.cde.ca.gov/cacs/<subject>.
## URL pattern
```
https://www2.cde.ca.gov/cacs/<subject>?c0=..&c1=..&c2=..&order=0&page=0&perpage=100&mingrade=0&maxgrade=12&dl=1
```
| param | meaning |
|---|---|
| subject | path segment: arts, cte, cs, ela, eld, health, history, math, pe, library, science, wl |
| c0, c1, c2 | filter levels (names vary by subject, see below). Comma-separate for several values: c1=2,3. Leave out unused levels. |
| mingrade / maxgrade | 0 = TK & K, 1-12 = grades 1-12. Both default to 0 (K only). |
| order | sort order, codes below |
| page / perpage | page index from 0; 10, 25 or 100 per page |
| dl | 0 = HTML results page, 1 = download the results as a file |

Verified so far: dl=1 returns the full result set as one CSV (row count matched the page's 'Showing X of Y' for ela c0=1&c1=2).

## Shared codes
order:

| code | label |
|---|---|
| 0 | Grade Range |
| 1 | Discipline |
| 2 | Subdiscipline |
| 3 | Artistic Process |
| 4 | Anchor Standard |
| 5 | Standard Identifier |

grades:

| code | label |
|---|---|
| 0 | TK & K |
| 1 | 1st |
| 2 | 2nd |
| 3 | 3rd |
| 4 | 4th |
| 5 | 5th |
| 6 | 6th |
| 7 | 7th |
| 8 | 8th |
| 9 | 9th |
| 10 | 10th |
| 11 | 11th |
| 12 | 12th |

## arts - Arts Standards
Base page: https://www2.cde.ca.gov/cacs/arts
Standards shown on the unfiltered page: 1027

### c0 = Discipline

| code | label |
|---|---|
| 1 | Dance |
| 2 | Media Arts |
| 3 | Music |
| 4 | Theatre |
| 5 | Visual Arts |

### c1 = Subdiscipline

| code | label |
|---|---|
| 1 | Composition and Theory |
| 2 | Ensembles |
| 3 | Harmonizing Instruments |
| 4 | Technology |
| 5 | TK-8 |

### c2 = Artistic Process

| code | label |
|---|---|
| 1 | Creating |
| 2 | Performing |
| 3 | Presenting (Visual Arts only) |
| 4 | Producing (Media Arts only) |
| 5 | Responding |
| 6 | Connecting |

### c3 = Anchor Standard

| code | label |
|---|---|
| 1 | 1: Generate and conceptualize artistic ideas and work |
| 2 | 2: Organize and develop artistic ideas and work |
| 3 | 3: Refine and complete artistic work |
| 4 | 4. Select, analyze, and interpret artistic work for presentation |
| 5 | 5: Develop and refine artistic techniques and work for presentation |
| 6 | 6: Convey meaning through the presentation of artistic work |
| 7 | 7: Perceive and analyze artistic work |
| 8 | 8: Interpret intent and meaning in artistic work |
| 9 | 9: Apply criteria to evaluate artistic work |
| 10 | 10: Synthesize and relate knowledge and personal experiences to make art |
| 11 | 11: Relate artistic ideas and works with societal, cultural, and historical context to deepen understanding |

Page notes:

- These Standards were approved by the CA State Board of Education in 2019.
- The Introduction to the standards and glossaries for all five disciplines can be downloaded at https://www.cde.ca.gov/be/st/ss/vapacontentstds.asp .

Open questions:

- [ ] Are these codes stable over time?
- [ ] Columns in this subject's dl=1 CSV:

## cte - Career Technical Education Standards
Base page: https://www2.cde.ca.gov/cacs/cte

Check by hand:

- No CriteriaForm found - page layout may have changed.

Open questions:

- [ ] Are these codes stable over time?
- [ ] Columns in this subject's dl=1 CSV:

## cs - Computer Science Standards
Base page: https://www2.cde.ca.gov/cacs/cs
Standards shown on the unfiltered page: 127

### c0 = Concept

| code | label |
|---|---|
| 1 | Algorithms & Programming |
| 2 | Computing Systems |
| 3 | Data & Analysis |
| 4 | Impacts of Computing |
| 5 | Networks & the Internet |

### c1 = Subconcept

| code | label |
|---|---|
| 1 | Algorithms |
| 2 | Collection, Visualization, & Transformation |
| 3 | Control |
| 4 | Culture |
| 5 | Cybersecurity |
| 6 | Devices |
| 7 | Hardware & Software |
| 8 | Inference & Models |
| 9 | Modularity |
| 10 | Network Communication & Organization |
| 11 | Program Development |
| 12 | Safety, Law, & Ethics |
| 13 | Social Interactions |
| 14 | Storage |
| 15 | Troubleshooting |
| 16 | Variables |

### c2 = Practice(s)

| code | label |
|---|---|
| 1 | Fostering an Inclusive Computing Culture |
| 2 | Collaborating Around Computing |
| 3 | Recognizing and Defining Computational Problems |
| 4 | Developing and Using Abstractions |
| 5 | Creating Computational Artifacts |
| 6 | Testing and Refining Computational Artifacts |
| 7 | Communicating About Computing |

Page notes:

- See K-12 Computer Science Framework for subpractices ( https://k12cs.org )
- These Standards were approved by the CA State Board of Education in 2018.

Open questions:

- [ ] Are these codes stable over time?
- [ ] Columns in this subject's dl=1 CSV:

## ela - English Language Arts Standards
Base page: https://www2.cde.ca.gov/cacs/ela
Standards shown on the unfiltered page: 568

### c0 = Subject Area

| code | label |
|---|---|
| 1 | English Language Arts & Literacy in History/Social Studies, Science, and Technical Subjects (K–5) |
| 2 | English Language Arts (6–12) |
| 3 | Literacy in History/Social Studies, Science, and Technical Subjects (6–12) |

### c1 = Domain

| code | label |
|---|---|
| 1 | Language |
| 2 | Reading: Foundational Skills |
| 3 | Reading: Informational Text |
| 4 | Reading: Literacy in History/Social Studies |
| 5 | Reading: Literacy in Science and Technical |
| 6 | Reading: Literature |
| 7 | Speaking and Listening |
| 8 | Writing |
| 9 | Writing: Literacy in History/Social Studies, Science, and Technical Subjects |

### c2 = Cluster

| code | label |
|---|---|
| 1 | Comprehension and Collaboration |
| 2 | Conventions of Standard English |
| 3 | Conventions of Standards English |
| 4 | Craft and Structure |
| 5 | Fluency |
| 6 | Integration of Knowledge and Ideas |
| 7 | Key Ideas and Details |
| 8 | Knowledge of Language |
| 9 | Phonics and Word Recognition |
| 10 | Phonological Awareness |
| 11 | Presentation of Knowledge and Ideas |
| 12 | Print Concepts |
| 13 | Production and Distribution of Writing |
| 14 | Range of Reading and Level of Text Complexity |
| 15 | Range of Writing |
| 16 | Research to Build and Present Knowledge |
| 17 | Text Types and Purposes |
| 18 | Vocabulary Acquisition and Use |

Page notes:

- An asterisk (*) notation indicates the reader should see “Research to Build and Present Knowledge” in Writing and “Comprehension and Collaboration” in Speaking and Listening for additional standards relevant to gathering, assessing, and applying information from print and digital sources.
- Standards with California additions appear with a “CA” notation at the end.
- For more information, see the College and Career Readiness Anchor Standards .
- These Standards were approved by the CA State Board of Education in 2010.

Check by hand:

- c2 possible duplicate: 2="Conventions of Standard English" / 3="Conventions of Standards English"

Open questions:

- [ ] Are these codes stable over time?
- [ ] Columns in this subject's dl=1 CSV:

## eld - English Language Development Standards
Base page: https://www2.cde.ca.gov/cacs/eld
Standards shown on the unfiltered page: 771

### c0 = Critical Principle

| code | label |
|---|---|
| 1 | Part I: Interacting in Meaningful Ways |
| 2 | Part II: Learning About How English Works |

### c1 = Cluster

| code | label |
|---|---|
| 1 | A. Collaborative |
| 2 | A. Structuring Cohesive Texts |
| 3 | B. Expanding and Enriching Ideas |
| 4 | B. Interpretive |
| 5 | C. Connecting and Condensing Ideas |
| 6 | C. Productive |

### c2 = Proficiency Level

| code | label |
|---|---|
| 1 | Bridging |
| 2 | Emerging |
| 3 | Expanding |

### c3 = Content Strand

| code | label |
|---|---|
| 1 | Adapting language choices |
| 2 | Analyzing language choices |
| 3 | Composing/Writing |
| 4 | Condensing ideas |
| 5 | Connecting ideas |
| 6 | Evaluating language choices |
| 7 | Exchanging information and ideas |
| 8 | Exchanging information/ideas |
| 9 | Interacting via written English |
| 10 | Justifying/arguing |
| 11 | Listening actively |
| 12 | Modifying to add details |
| 13 | Offering opinions |
| 14 | Presenting |
| 15 | Reading/viewing closely |
| 16 | Selecting language resources |
| 17 | Supporting opinions |
| 18 | Supporting opinions and persuading others |
| 19 | Understanding cohesion |
| 20 | Understanding text structure |
| 21 | Using nouns and noun phrases |
| 22 | Using verbs and verb phrases |
| 23 | Writing |

Page notes:

- These Standards were approved by the CA State Board of Education in 2012.

Open questions:

- [ ] Are these codes stable over time?
- [ ] Columns in this subject's dl=1 CSV:

## health - Health Education Standards
Base page: https://www2.cde.ca.gov/cacs/health
Standards shown on the unfiltered page: 854

### c0 = Content Area

| code | label |
|---|---|
| 1 | Alcohol, Tobacco, and Other Drugs |
| 2 | Growth and Development |
| 3 | Growth, Development, and Sexual Health |
| 4 | Injury, Prevention, and Safety |
| 5 | Mental, Emotional, and Social Health |
| 6 | Nutrition and Physical Activity |
| 7 | Personal and Community Health |

### c1 = Overarching Content Standard

| code | label |
|---|---|
| 1 | 1: Essential Concepts |
| 2 | 2: Analyzing Influences |
| 3 | 3: Accessing Valid Health Information |
| 4 | 4: Interpersonal Communication |
| 5 | 5: Decision Making |
| 6 | 6: Goal Setting |
| 7 | 7: Practicing Health-Enhancing Behaviors |
| 8 | 8: Health Promotion |

Page notes:

- The Health Education Standards were developed for Kindergarten through Grade 12.
- The Health Education Standards for Grades 7-8 and Grades 9-12 were developed for grade bands (e.g. Grade 10 Standards are within Grades 9-12 Standards).
- Standards for Growth, Development, and Sexual Health were developed for Grade 5, Grades 7-8, and Grades 9-12 only.
- These Standards were approved by the CA State Board of Education in 2008.

Open questions:

- [ ] Are these codes stable over time?
- [ ] Columns in this subject's dl=1 CSV:

## history - History–Social Science Standards
Base page: https://www2.cde.ca.gov/cacs/history
Standards shown on the unfiltered page: 618

### c0 = Course

| code | label |
|---|---|
| 1 | Learning and Working Now and Long Ago, Grade K |
| 2 | A Child’s Place in Time and Space, Grade 1 |
| 3 | People Who Make a Difference, Grade 2 |
| 4 | Continuity and Change, Grade 3 |
| 5 | California: A Changing State, Grade 4 |
| 6 | United States History and Geography: Making a New Nation, Grade 5 |
| 7 | World History and Geography: Ancient Civilizations, Grade 6 |
| 8 | World History and Geography: Medieval and Early Modern Times, Grade 7 |
| 9 | United States History and Geography: Growth and Conflict, Grade 8 |
| 10 | World History, Culture, and Geography: The Modern World, Grade 10 |
| 11 | United States History and Geography: Continuity and Change in the Twentieth Century, Grade 11 |
| 12 | Principles of American Democracy, Grade 12 |
| 13 | Principles of Economics, Grade 12 |

Page notes:

- Historical and Social Sciences Analysis Skills
- These Standards were approved by the CA State Board of Education in 1998.

Open questions:

- [ ] Are these codes stable over time?
- [ ] Columns in this subject's dl=1 CSV:

## math - Mathematics Standards
Base page: https://www2.cde.ca.gov/cacs/math
Standards shown on the unfiltered page: 734

### c0 = Domain

| code | label |
|---|---|
| 1 | Arithmetic with Polynomials and Rational Expressions |
| 2 | Building Functions |
| 3 | Circles |
| 4 | Conditional Probability and the Rules of Probability |
| 5 | Congruence |
| 6 | Counting and Cardinality |
| 7 | Creating Equations |
| 8 | Expressing Geometric Properties with Equations |
| 9 | Expressions and Equations |
| 10 | Functions |
| 11 | Geometric Measurement and Dimension |
| 12 | Geometry |
| 13 | Interpreting Categorical and Quantitative Data |
| 14 | Interpreting Functions |
| 15 | Linear, Quadratic, and Exponential Models |
| 16 | Making Inferences and Justifying Conclusions |
| 17 | Measurement and Data |
| 18 | Modeling with Geometry |
| 19 | Number and Operations in Base Ten |
| 20 | Number and Operations—Fractions |
| 21 | Operations and Algebraic Thinking |
| 22 | Quantities |
| 23 | Ratios and Proportional Relationships |
| 24 | Reasoning with Equations and Inequalities |
| 25 | Seeing Structure in Expressions |
| 26 | Similarity, Right Triangles, and Trigonometry |
| 27 | Statistics and Probability |
| 28 | The Complex Number System |
| 29 | The Number System |
| 30 | The Real Number System |
| 31 | Trigonometric Functions |
| 32 | Using Probability to Make Decisions |

### c1 = Discipline

| code | label |
|---|---|
| 1 | Algebra I |
| 2 | Algebra II |
| 3 | Calculus |
| 4 | Geometry |
| 5 | Math I |
| 6 | Math II |
| 7 | Math III |
| 8 | Statistics and Probability |
| 9 | Statistics and Probability (AP) |

### c2 = Conceptual Category

| code | label |
|---|---|
| 1 | Algebra |
| 2 | Functions |
| 3 | Geometry |
| 4 | Number and Quantity |
| 5 | Statistics and Probability |

Page notes:

- * Indicates a modeling standard linking mathematics to everyday life, work, and decision-making.
- (+) Indicates additional mathematics to prepare students for advanced courses.
- Some standards are repeated in multiple higher mathematics courses; therefore instructional notes, which appear in brackets, indicate what is appropriate for study in this particular course.
- Standards with California additions appear with a "CA" notation at the end.
- Standards for Mathematical Practice
- These Standards were approved by the CA State Board of Education in 2010, and updated in 2013.

Open questions:

- [ ] Are these codes stable over time?
- [ ] Columns in this subject's dl=1 CSV:

## pe - Physical Education Standards
Base page: https://www2.cde.ca.gov/cacs/pe
Standards shown on the unfiltered page: 744

### c0 = Cluster

| code | label |
|---|---|
| 1 | Aerobic Capacity |
| 2 | Assessment |
| 3 | Body Composition |
| 4 | Body Management |
| 5 | Combinations of Movement Patterns and Skills |
| 6 | Fitness Concepts |
| 7 | Flexibility |
| 8 | Group Dynamics |
| 9 | Locomotor Movement |
| 10 | Manipulative Skills |
| 11 | Movement Concepts |
| 12 | Muscular Strength/Endurance |
| 13 | Rhythmic Skills |
| 14 | Self-Responsibility |
| 15 | Social Interaction |

Page notes:

- High School Courses 1 and 2 are designed to be completed before a student enrolls in any High School Course 3.
- High School Courses 1, 2, and 3 are designed to be completed before a student enrolls in any High School Course 4.
- These Standards were approved by the CA State Board of Education in 2005.

Open questions:

- [ ] Are these codes stable over time?
- [ ] Columns in this subject's dl=1 CSV:

## library - School Library Standards
Base page: https://www2.cde.ca.gov/cacs/library
Standards shown on the unfiltered page: 117

### c0 = Overarching Standard

| code | label |
|---|---|
| 1 | 1. Students access information |
| 2 | 2. Students evaluate information |
| 3 | 3. Students use information |
| 4 | 4. Students integrate information literacy skills into all areas of learning |

Page notes:

- These Standards were approved by the CA State Board of Education in 2010.

Open questions:

- [ ] Are these codes stable over time?
- [ ] Columns in this subject's dl=1 CSV:

## science - Science (CA NGSS) Standards
Base page: https://www2.cde.ca.gov/cacs/science
Standards shown on the unfiltered page: 220

### c0 = Disciplinary Core Idea

| code | label |
|---|---|
| 1 | ESS1.A: The Universe and its Stars |
| 2 | ESS1.B: Earth and the Solar System |
| 3 | ESS1.C: The History of Planet Earth |
| 4 | ESS2.A: Earth Materials and Systems |
| 5 | ESS2.B: Plate Tectonics and Large-Scale System Interactions |
| 6 | ESS2.C: The Roles of Water in Earth's Surface Processes |
| 7 | ESS2.D: Weather and Climate |
| 8 | ESS2.E: Biogeology |
| 9 | ESS3.A: Natural Resources |
| 10 | ESS3.B: Natural Hazards |
| 11 | ESS3.C: Human Impacts on Earth Systems |
| 12 | ESS3.D: Global Climate Change |
| 13 | ETS1.A: Defining and Delimiting Engineering Problems |
| 14 | ETS1.B: Developing Possible Solutions |
| 15 | ETS1.C: Optimizing the Design Solution |
| 16 | LS1.A: Structure and Function |
| 17 | LS1.B: Growth and Development of Organisms |
| 18 | LS1.C: Organization for Matter and Energy Flow in Organisms |
| 19 | LS1.D: Information Processing |
| 20 | LS2.A: Interdependent Relationships in Ecosystems |
| 21 | LS2.B: Cycles of Matter and Energy Transfer in Ecosystems |
| 22 | LS2.C: Ecosystem Dynamics, Functioning, and Resilience |
| 23 | LS2.D: Social Interactions and Group Behavior |
| 24 | LS3.A: Inheritance of Traits |
| 25 | LS3.B: Variation of Traits |
| 26 | LS4.A: Evidence of Common Ancestry and Diversity |
| 27 | LS4.B: Natural Selection |
| 28 | LS4.C: Adaptation |
| 29 | LS4.D: Biodiversity and Humans |
| 30 | PS1.A: Structure and Properties of Matter |
| 31 | PS1.B: Chemical Reactions |
| 32 | PS1.C: Nuclear Processes |
| 33 | PS2.A: Forces and Motion |
| 34 | PS2.B: Types of Interactions |
| 35 | PS3.A: Definitions of Energy |
| 36 | PS3.B: Conservation of Energy and Energy Transfer |
| 37 | PS3.C: Relationship between Energy and Forces |
| 38 | PS3.D: Energy in Chemical Processes |
| 39 | PS4.A: Wave Properties |
| 40 | PS4.B: Electromagnetic Radiation |
| 41 | PS4.C: Information Technologies and Instrumentation |

### c1 = Cross Cutting Concept

| code | label |
|---|---|
| 1 | CCC-1: Patterns |
| 2 | CCC-2: Cause and Effect: Mechanism and Explanation |
| 3 | CCC-3: Scale, Proportion, and Quantity |
| 4 | CCC-4: Systems and Systems Models |
| 5 | CCC-5: Energy and Matter: Flows, Cycles, and Conservation |
| 6 | CCC-6: Structure and Function |
| 7 | CCC-7: Stability and Change |

### c2 = Science & Engineering Practice

| code | label |
|---|---|
| 1 | SEP-1: Asking Questions and Defining Problems |
| 2 | SEP-2: Developing and Using Models |
| 3 | SEP-3: Planning and Carrying Out Investigations |
| 4 | SEP-4: Analyzing and Interpreting Data |
| 5 | SEP-5: Using Mathematics and Computational Thinking |
| 6 | SEP-6: Constructing Explanations and Designing Solutions |
| 7 | SEP-7: Engaging in Argument From Science |
| 8 | SEP-8: Obtaining, Evaluating, and Communicating Information |

### c3 = Content Area

| code | label |
|---|---|
| 1 | Earth and Space Science |
| 2 | Engineering, Technology, and Applications of Science |
| 3 | Life Science |
| 4 | Physical Science |

Page notes:

- * Indicates performance expectations that integrate traditional science content with engineering through a Practice or Disciplinary Core Ideas.
- ** California clarification statements, marked with double asterisks, were incorporated by the California Science Expert Review Panel.
- California Common Core State Standard Connections for Mathematics which begin “MP” can be found in the Standards for Mathematical Practice
- These Standards were approved by the CA State Board of Education in 2013

Open questions:

- [ ] Are these codes stable over time?
- [ ] Columns in this subject's dl=1 CSV:

## wl - World Languages Standards
Base page: https://www2.cde.ca.gov/cacs/wl
Standards shown on the unfiltered page: 52

### c0 = Strand

| code | label |
|---|---|
| 1 | Communication |
| 2 | Connections |
| 3 | Cultures |

### c1 = Substrand

| code | label |
|---|---|
| 1 | Connections to Other Disciplines |
| 2 | Cultural Comparisons |
| 3 | Cultural Products, Practices, and Perspectives |
| 4 | Culturally Appropriate Interaction |
| 5 | Diverse Perspectives and Distinctive Viewpoints |
| 6 | Intercultural Influences |
| 7 | Interpersonal Communication |
| 8 | Interpretive Communication |
| 9 | Language Comparisons in Service of Communication |
| 10 | Presentational Communication |
| 11 | Productive Structures in Service of Communication |
| 12 | Receptive Structures in Service of Communication |
| 13 | Settings for Communication |

Page notes:

- These Standards were approved by the CA State Board of Education in 2019.

Open questions:

- [ ] Are these codes stable over time?
- [ ] Columns in this subject's dl=1 CSV:
