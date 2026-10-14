0003 Treat ELA cluster 3 "Conventions of Standards English" as cluster 2

Status: accepted, 2026-10-08

Store each standard's original CDE cluster code, and add a cluster alias table mapping ELA cluster 3 to cluster 2. Progressions, joins, and queries use the merged cluster.

The two codes split one cluster by grade band with no overlap. With grades TK–12:
- `c2=3` "Conventions of Standards English" returned 6 standards: L.6.1, L.6.2, L.7.1, L.7.2, L.8.1, L.8.2. With grades TK–5 it returned 0.
- `c2=2` "Conventions of Standard English" returned 16: L.K.1/2 through L.5.1/2, L.9-10.1/2, L.11-12.1/2. None from grades 6–8.

Together they make 22 standards and an unbroken K–12 sequence for L.1 and L.2. Every L.x.1 opens with the same stem ("Demonstrate command of the conventions of standard English grammar and usage when writing or speaking") and every L.x.2 with its own shared stem, across both codes.

The misspelling follows a batch of entries, not the subject area. Grades 6–8 and 9–12 are both under subject area 2, "English Language Arts (6–12)", but only 6–8 carry the misspelled cluster.

Without the alias, a query on cluster 2 alone leaves a three-grade gap in the middle of the L.1 and L.2 progressions. When filtering downloads by cluster, request `c2=2,3`. Full-subject downloads already include both.

`cacs_codes.py` flags this automatically as a possible duplicate (labels that match after dropping a plural s). Other subjects may have similar duplicates; check its warnings for each subject.
