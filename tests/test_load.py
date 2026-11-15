"""
Tests for src/load.py. Run from the project root:

    python -m unittest discover tests -v

unittest is Python's built-in test tool, so nothing needs installing.

The first class tests the small functions on their own. The second builds a
real database from data/raw/ into a temporary folder and checks the cases the
decision records single out as easy to get wrong.
"""
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import load  # noqa: E402  (must come after the sys.path line above)


class SmallFunctions(unittest.TestCase):

    def test_grade(self):
        self.assertEqual(load.parse_grade("K"), (0, 0))
        self.assertEqual(load.parse_grade("5"), (5, 5))
        self.assertEqual(load.parse_grade("9–10"), (9, 10))   # en dash, as on the site
        self.assertEqual(load.parse_grade("9-10"), (9, 10))        # hyphen, as in identifiers
        for bad in ("", "13", "10-9", "K-2-3", "ninth"):
            with self.assertRaises(load.LoadError):
                load.parse_grade(bad)

    def test_identifier_norm_changes_only_en_dashes(self):
        self.assertEqual(load.normalize_identifier("RH.6–8.1"), "RH.6-8.1")
        self.assertEqual(load.normalize_identifier("RL.2..2"), "RL.2..2")   # not repaired

    def test_search_form(self):
        self.assertEqual(load.search_form("f(n − 1) and (x – p)"), "f(n - 1) and (x - p)")

    def test_ela_identifier(self):
        p = load.parse_identifier("ela", "L.9-10.1")
        self.assertEqual((p["strand"], p["grade"], p["number"]), ("L", "9-10", "1"))
        self.assertIsNone(load.parse_identifier("ela", "RL.2..2"))

    def test_eld_identifier(self):
        p = load.parse_identifier("eld", "ELD.PI.K.12b.Em")
        self.assertEqual((p["strand"], p["grade"], p["number"], p["letter"], p["level"]),
                         ("PI", "K", "12", "b", "Em"))
        self.assertIsNone(load.parse_identifier("eld", "ELD.PI.12a.Br"))    # grade missing

    def test_math_identifier(self):
        p = load.parse_identifier("math", "5.NF.3.a")
        self.assertEqual((p["strand"], p["grade"], p["number"], p["letter"], p["parent"]),
                         ("NF", "5", "3", "a", "5.NF.3"))
        p = load.parse_identifier("math", "A-CED.1")
        self.assertEqual((p["strand"], p["grade"], p["number"], p["parent"]),
                         ("A-CED", None, "1", None))
        # 3.1 is a California standard placed after G-GPE.3, not a part of it.
        p = load.parse_identifier("math", "G-GPE.3.1")
        self.assertEqual((p["number"], p["letter"], p["parent"]), ("3.1", None, None))
        self.assertEqual(load.parse_identifier("math", "Calculus.16.0")["strand"], "Calculus")

    def test_sub_items(self):
        stem, items = load.split_sub_items("Stem line.\na. First.\nb. Second,\nwrapped.\nc. Third.")
        self.assertEqual(stem, "Stem line.")
        self.assertEqual(items, [("a", "First."), ("b", "Second, wrapped."), ("c", "Third.")])

    def test_sub_items_accepts_cde_typos(self):
        _, items = load.split_sub_items("Stem.\na. One.\nb. Two.\nc . Three.\nd.Four.")
        self.assertEqual([letter for letter, _ in items], ["a", "b", "c", "d"])

    def test_sub_items_ignores_a_letter_out_of_turn(self):
        stem, items = load.split_sub_items("Use sources\ne. g. letters.")
        self.assertEqual((stem, items), ("Use sources e. g. letters.", []))

    def test_flags(self):
        self.assertEqual(load.flags("Blend phonemes. CA"), (1, 0))
        self.assertEqual(load.flags("Ensure agreement.*"), (0, 1))
        self.assertEqual(load.flags("CALCULATE the sum."), (0, 0))

    def test_placeholder(self):
        self.assertTrue(load.is_placeholder("(Begins in grade 2) CA"))
        self.assertTrue(load.is_placeholder("(Not applicable to literature)"))
        # "(+)" opens a real high school standard.
        self.assertFalse(load.is_placeholder("(+) Extend polynomial identities to the complex numbers."))


class BuiltDatabase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        db = Path(cls.tmp.name) / "standards.db"
        # Built with the identifier corrections but without the imported
        # Learning Commons edges, so these tests check only what the loader makes.
        cls.summary = load.build(ROOT / "data" / "raw", ROOT / "docs" / "reference" / "codes.csv",
                                 ROOT / "src" / "schema.sql", db,
                                 ROOT / "data" / "curated" / "identifier_corrections.csv")
        cls.con = sqlite3.connect(db)

    @classmethod
    def tearDownClass(cls):
        cls.con.close()
        cls.tmp.cleanup()

    def q(self, sql, *args):
        return self.con.execute(sql, args).fetchall()

    def test_record_counts_match_the_scrapes(self):
        # 0011: math 734, ELA 568, ELD 771.
        self.assertEqual(dict(self.q("SELECT subject, COUNT(*) FROM standards GROUP BY 1")),
                         {"math": 734, "ela": 568, "eld": 771})

    def test_one_identifier_several_records(self):
        # 0011: A-CED.1 is a separate record in five courses.
        rows = self.q("SELECT record_id, discipline FROM standards WHERE identifier = 'A-CED.1'")
        self.assertEqual(len(rows), 5)
        self.assertIn((558, "Algebra I"), rows)
        self.assertIn((721, "Math I"), rows)

    def test_calculus_16_is_two_standards(self):
        rows = self.q("SELECT record_id, text_standard FROM standards "
                      "WHERE identifier = 'Calculus.16.0' ORDER BY record_id")
        self.assertEqual([r[0] for r in rows], [4762, 4763])
        self.assertNotEqual(rows[0][1], rows[1][1])

    def test_dashes(self):
        # 0012: the identifier keeps CDE's en dash; the normalized copy has a hyphen.
        self.assertEqual(self.q("SELECT identifier, grade_min, grade_max FROM standards "
                                "WHERE identifier_norm = 'RH.6-8.1'"), [("RH.6–8.1", 6, 8)])
        # F-IF.3 writes f(n − 1) with a minus sign; a keyboard hyphen must find it.
        self.assertTrue(self.q("SELECT 1 FROM standards WHERE identifier = 'F-IF.3' "
                               "AND text_search LIKE '%n - 1%'"))
        self.assertTrue(self.q("SELECT 1 FROM standards WHERE identifier = 'F-IF.3' "
                               "AND text_standard LIKE '%n − 1%'"))

    def test_malformed_identifiers_are_kept_and_read_through_corrections(self):
        # The identifier stays as CDE wrote it; the parts come from the correction.
        self.assertEqual(self.q("SELECT identifier, identifier_norm, identifier_corrected, "
                                "id_strand, id_grade, id_number FROM standards WHERE record_id = 5604"),
                         [("RL.2..2", "RL.2..2", "RL.2.2", "RL", "2", "2")])
        self.assertEqual(self.q("SELECT identifier, id_grade, id_number, id_letter FROM standards "
                                "WHERE record_id = 7276"), [("ELD.PI.12a.Em", "4", "12", "a")])
        self.assertEqual(self.q("SELECT identifier, id_number FROM standards WHERE record_id = 7480"),
                         [("ELD.PI.7.78.Em", "8")])
        self.assertEqual(self.summary["unparsed"], [])
        self.assertEqual(len(self.summary["corrected"]), 7)

    def test_without_corrections_the_malformed_ones_are_reported(self):
        codes = load.read_codes(ROOT / "docs" / "reference" / "codes.csv")
        unparsed = []
        for subject in ("ela", "eld"):
            path = load.newest_records_file(ROOT / "data" / "raw", subject)
            unparsed += [i for _, i in load.read_records(path, subject, codes)[2]["unparsed"]]
        self.assertEqual(sorted(unparsed), ["ELD.PI.12a.Br", "ELD.PI.12a.Em", "ELD.PI.12a.Ex",
                                            "RL.2..2", "RL.2..3"])

    def chain(self, where):
        return self.q("SELECT a.identifier, b.identifier FROM edges e "
                      "JOIN standards a ON a.record_id = e.from_record_id "
                      "JOIN standards b ON b.record_id = e.to_record_id "
                      f"WHERE {where} ORDER BY a.grade_min, a.identifier, b.identifier")

    def test_ela_progression(self):
        # 0005: every L.x.1 from K to 11-12, in grade order.
        links = self.chain("e.type = 'next_grade' AND a.id_strand = 'L' AND a.id_number = '1'")
        self.assertEqual(links[0], ("L.K.1", "L.1.1"))
        self.assertEqual(links[-1], ("L.9-10.1", "L.11-12.1"))
        self.assertEqual(len(links), 10)

    def test_progression_skips_placeholders(self):
        # L.K.3 and L.1.3 read "(Begins in grade 2)"; the chain starts at grade 2.
        links = self.chain("e.type = 'next_grade' AND a.id_strand = 'L' AND a.id_number = '3'")
        self.assertEqual(links[0], ("L.2.3", "L.3.3"))
        self.assertEqual(self.q("SELECT COUNT(*) FROM standards WHERE is_placeholder = 1"), [(24,)])

    def test_eld_progression_where_lettering_changes(self):
        # ELD.PI.3.6 becomes 6a and 6b in grade 4.
        links = self.chain("e.type = 'next_grade' AND a.identifier = 'ELD.PI.3.6.Em'")
        self.assertEqual(links, [("ELD.PI.3.6.Em", "ELD.PI.4.6a.Em"), ("ELD.PI.3.6.Em", "ELD.PI.4.6b.Em")])

    def test_eld_levels(self):
        links = self.chain("e.type = 'next_level' AND a.identifier LIKE 'ELD.PI.K.1.%'")
        self.assertEqual(links, [("ELD.PI.K.1.Em", "ELD.PI.K.1.Ex"), ("ELD.PI.K.1.Ex", "ELD.PI.K.1.Br")])
        # The mistyped record joins its Expanding sibling through the correction.
        self.assertIn(("ELD.PI.7.78.Em", "ELD.PI.7.8.Ex"), self.chain("e.type = 'next_level'"))

    def test_no_edge_is_marked_reviewed(self):
        self.assertEqual(self.q("SELECT COUNT(*) FROM edges WHERE reviewed <> 0"), [(0,)])

    def test_identifier_grade_agrees_with_grade_field(self):
        self.assertEqual(self.summary["grade_mismatch"], [])

    def test_cluster_alias(self):
        # 0003: grades 6-8 carry the misspelled cluster, code 3; it is read as code 2.
        self.assertEqual(self.q("SELECT cluster_code, cluster_code_merged FROM standards "
                                "WHERE identifier = 'L.6.1'"), [(3, 2)])
        merged = self.q("SELECT COUNT(*) FROM standards WHERE subject = 'ela' "
                        "AND cluster_code_merged = 2")
        self.assertEqual(merged, [(22,)])

    def test_ela_sub_items(self):
        letters = [r[0] for r in self.q(
            "SELECT letter FROM sub_items JOIN standards USING (record_id) "
            "WHERE identifier = 'L.5.1' ORDER BY letter")]
        self.assertEqual(letters, ["a", "b", "c", "d", "e"])
        # RF.2.3 has "c . Decode"; without the typo rule the letters stop at b.
        letters = [r[0] for r in self.q(
            "SELECT letter FROM sub_items JOIN standards USING (record_id) "
            "WHERE identifier = 'RF.2.3' ORDER BY letter")]
        self.assertEqual(letters, ["a", "b", "c", "d", "e", "f"])

    def test_text_is_stored_as_written(self):
        import csv
        with open(ROOT / "data" / "raw" / self.summary["subjects"]["math"]["file"],
                  encoding="utf-8", newline="") as f:
            source = {int(r["record_id"]): r["text_Standard"] for r in csv.DictReader(f)}
        stored = dict(self.q("SELECT record_id, text_standard FROM standards WHERE subject = 'math'"))
        self.assertEqual(stored, source)

    def test_build_info(self):
        self.assertEqual(self.q("SELECT value FROM build_info WHERE key = 'schema_version'"),
                         [(load.SCHEMA_VERSION,)])
        self.assertEqual(len(self.q("SELECT * FROM source_files")), 3)


class StopsRatherThanGuesses(unittest.TestCase):

    def test_unknown_column_stops_the_load(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ela_records_2099-01-01.csv"
            path.write_text("record_id,url,identifier,Grade,text_Standard,page,Surprise\n"
                            "1,https://www2.cde.ca.gov/cacs/id/web/1,L.1.1,1,Text.,0,x\n",
                            encoding="utf-8")
            with self.assertRaises(load.LoadError):
                load.read_records(path, "ela", {})

    def test_correction_for_a_changed_identifier_stops_the_load(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ela_records_2099-01-01.csv"
            path.write_text("record_id,url,identifier,Grade,text_Standard,page\n"
                            "1,https://www2.cde.ca.gov/cacs/id/web/1,L.1.1,1,Text.,0\n",
                            encoding="utf-8")
            fix = {1: {"identifier": "L.1..1", "corrected_identifier": "L.1.1"}}
            with self.assertRaises(load.LoadError):
                load.read_records(path, "ela", {}, fix)

    def test_label_missing_from_codes_stops_the_load(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ela_records_2099-01-01.csv"
            path.write_text("record_id,url,identifier,Grade,Cluster,text_Standard,page\n"
                            "1,https://www2.cde.ca.gov/cacs/id/web/1,L.1.1,1,Not A Cluster,Text.,0\n",
                            encoding="utf-8")
            with self.assertRaises(load.LoadError):
                load.read_records(path, "ela", {})


if __name__ == "__main__":
    unittest.main()
