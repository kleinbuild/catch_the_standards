"""
Tests for the parent standards and math links that come from Learning Commons.

    python -m unittest discover tests -v

These build the database with the committed files in data/derived/, so they
check the files as well as the loader. They need no Learning Commons download.
"""
import csv
import sqlite3
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import load    # noqa: E402
import lookup  # noqa: E402

DERIVED = ROOT / "data" / "derived"


class ParentsAndLinks(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        db = Path(cls.tmp.name) / "standards.db"
        load.build(ROOT / "data" / "raw", ROOT / "docs" / "reference" / "codes.csv",
                   ROOT / "src" / "schema.sql", db,
                   ROOT / "data" / "curated" / "identifier_corrections.csv",
                   DERIVED / "learning_commons_edges.csv",
                   DERIVED / "learning_commons_parents.csv")
        cls.con = sqlite3.connect(db)
        cls.con.row_factory = sqlite3.Row
        with open(DERIVED / "learning_commons_edges.csv", encoding="utf-8", newline="") as f:
            cls.edges = list(csv.DictReader(f))

    @classmethod
    def tearDownClass(cls):
        cls.con.close()
        cls.tmp.cleanup()

    def q(self, sql, *args):
        return [tuple(r) for r in self.con.execute(sql, args)]

    def test_cde_records_are_untouched(self):
        self.assertEqual(self.q("SELECT COUNT(*) FROM standards WHERE origin = 'cde'"), [(2073,)])
        self.assertEqual(self.q("SELECT COUNT(*) FROM standards WHERE origin = 'cde' "
                                "AND (record_id <= 0 OR url IS NULL)"), [(0,)])

    def test_added_rows_cannot_be_taken_for_cde_records(self):
        self.assertEqual(self.q("SELECT COUNT(*) FROM standards WHERE origin <> 'cde' "
                                "AND (record_id >= 0 OR url IS NOT NULL OR subject <> 'math')"),
                         [(0,)])

    def test_the_parent_of_4_NF_3_a(self):
        row = self.q("SELECT p.identifier, p.origin, p.grade_min, p.domain FROM standards c "
                     "JOIN standards p ON p.record_id = c.parent_record_id "
                     "WHERE c.identifier = '4.NF.3.a'")
        self.assertEqual(row, [("4.NF.3", "learning_commons", 4, "Number and Operations—Fractions")])

    def test_every_math_sub_item_record_has_a_parent_row(self):
        self.assertEqual(self.q("SELECT COUNT(*) FROM standards "
                                "WHERE parent_identifier_norm IS NOT NULL "
                                "AND parent_record_id IS NULL"), [(0,)])

    def test_a_parent_is_in_the_same_course_as_its_parts(self):
        self.assertEqual(self.q("SELECT COUNT(*) FROM standards c JOIN standards p "
                                "ON p.record_id = c.parent_record_id "
                                "WHERE COALESCE(c.discipline, '') <> COALESCE(p.discipline, '')"),
                         [(0,)])

    def test_a_k8_published_link_is_one_link(self):
        # A link Learning Commons publishes between two K-8 standards must not
        # be copied onto sub-items.
        k8 = [e for e in self.edges if "high school" not in e["note"]]
        per_published_link = Counter(e["lc_relationship_id"] for e in k8)
        self.assertEqual(max(per_published_link.values()), 1)

    def test_no_link_is_spread_over_sub_items(self):
        self.assertEqual([e for e in self.edges if "sub-items" in e["note"]], [])

    def test_high_school_links_stay_within_a_pathway(self):
        course = dict(self.q("SELECT record_id, COALESCE(discipline, '') FROM standards"))
        traditional = {"Algebra I", "Geometry", "Algebra II"}
        integrated = {"Math I", "Math II", "Math III"}
        for e in self.edges:
            pair = {course[int(e["from_record_id"])], course[int(e["to_record_id"])]}
            self.assertFalse(pair & traditional and pair & integrated, e)

    def test_lookup_from_a_sub_item_includes_what_its_parent_builds_on(self):
        # Take any link that ends on an added parent, and one of that parent's parts.
        link = self.q("SELECT e.from_record_id, e.to_record_id FROM edges e JOIN standards p "
                      "ON p.record_id = e.to_record_id WHERE p.origin = 'learning_commons' LIMIT 1")
        self.assertTrue(link)
        earlier, parent = link[0]
        part = self.q("SELECT record_id FROM standards WHERE parent_record_id = ? LIMIT 1", parent)[0][0]
        found, _ = lookup.walk_back(self.con, part, 1)
        self.assertIn((earlier, parent), [(rid, via) for _, rid, via, *_ in found])

    def test_no_edge_is_marked_reviewed(self):
        self.assertEqual(self.q("SELECT COUNT(*) FROM edges WHERE reviewed <> 0"), [(0,)])


if __name__ == "__main__":
    unittest.main()
