0009 Store method guidance as sourced records scoped by target type, learning stage, and population; match them, do not rank them

Status: proposed, 2026-10-14

The tool shows guidance about teaching methods whose stated scope matches the teacher's situation. It does not choose or rank methods. The teacher picks.

Guidance goes in its own table. Each row holds: the method or practice, a source citation and link, the scope the source states, the evidence strength the source states, and `reviewed`. Guidance links to standards through target type and concept tags, not standard by standard, so one source is not copied onto hundreds of rows. This follows the edges model in 0006: sourced, typed, reviewable.

Scope is recorded exactly as the source states it, not widened. McCallum, "Strike Three" (Mathematical Musings), shows how this goes wrong. Gersten et al. 2009 (IES) limits its explicit-instruction recommendation to Tier 2 and Tier 3 and says it makes no recommendations for general classroom instruction. Hughes et al. 2017 then cites it, along with four other IES guides, for math students in general. Those four guides recommend different methods for different targets: conceptual work for fractions (Siegler 2010), mixed methods for problem solving (Woodward 2012), structured discovery paired with explicit instruction for young children (Frye 2013), and strategy comparison for algebra (Star 2015). Kroesbergen and Van Luit 2003 found direct instruction effective for basic computation with students with special needs, but not for problem solving.

There are three scope dimensions.

Target type is a property of a standard or sub-item. Its values are `fact_fluency`, `procedural_fluency`, `conceptual`, and `application`; a standard can carry more than one. Fact fluency is recall of basic facts (2.OA.2, 3.OA.7). Procedural fluency is executing algorithms (4.NBT.4, 5.NBT.5), the term from National Research Council, Adding It Up (2001). A script suggests tags from the standard's wording ("fluently", "understand", "solve word problems", "real-world") with `reviewed=0`, and the owner confirms them.

Learning stage comes from the instructional hierarchy: `acquisition`, `fluency`, `generalization`, `adaptation`. It describes a student's position on a concept, not a property of a standard. One student can be at different stages on different concepts. Stage `fluency` is separate from target types `fact_fluency` and `procedural_fluency`. Every skill, conceptual ones included, passes through a fluency stage.

Population is optional. Its fields are tier or setting, grade band or age, EL status, ELD proficiency level, and dual identification (IEP plus EL). ELD level uses the same Em/Ex/Br codes as the ELD identifiers (0005). EL scope matters most for word problems and new discipline vocabulary.

On guidance rows, all three dimensions are scope fields. The teacher gives stage and population at query time, and the database does not store them. That keeps student information, which is IEP-adjacent, out of the database.

When no guidance matches, the tool shows the nearest guidance marked as outside its stated scope, and says that nothing in the database covers the case. This is expected to be common for older students relearning earlier-grade standards. No source reviewed so far addresses that case directly.

Not decided:
- whether disability category is a population field
- the evidence-strength scale: each source's own (for example, IES ratings) or one common scale
- the starting source list: the five IES guides above, plus Fuchs et al. 2021 (IES), which has not been read
- whether practitioner and curriculum sources are allowed, and how they are marked apart from research syntheses
