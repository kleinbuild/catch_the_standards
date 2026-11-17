"""
Tests for how the loader applies the owner's decisions from review sheets.

    python -m unittest discover tests -v

Each test writes a small sheet into a temporary folder; the real sheets in
data/curated/review/ are not touched.
"""
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import load  # noqa: E402

HEADER = "decision,owner_note,from_record_id,to_record_id,type,reviewed\n"
# Record IDs: L.3.1 = 5685, L.4.1 = 5729, L.5.1 = 5773, 1.G.2 = 301, 3.MD.5.a = 355.


WITH_CONFIDENCE = "decision,confidence,owner_note,from_record_id,to_record_id,type,reviewed\n"


def confidence_after(sheet_rows):
    """Build with a sheet that has the confidence column. Returns {link: confidence}."""
    with tempfile.TemporaryDirectory() as tmp:
        review = Path(tmp) / "review"
        review.mkdir()
        (review / "links.csv").write_text(WITH_CONFIDENCE + sheet_rows, encoding="utf-8")
        db = Path(tmp) / "standards.db"
        load.build(ROOT / "data" / "raw", ROOT / "docs" / "reference" / "codes.csv",
                   ROOT / "src" / "schema.sql", db,
                   ROOT / "data" / "curated" / "identifier_corrections.csv", review_dir=review)
        con = sqlite3.connect(db)
        found = {(a, b, kind): c for a, b, kind, c in con.execute(
            "SELECT from_record_id, to_record_id, type, confidence FROM edges")}
        con.close()
        return found


def build_with(sheet_rows):
    """Build a database with one review sheet holding `sheet_rows`. Returns (summary, edges)."""
    with tempfile.TemporaryDirectory() as tmp:
        review = Path(tmp) / "review"
        review.mkdir()
        (review / "links.csv").write_text(HEADER + sheet_rows, encoding="utf-8")
        db = Path(tmp) / "standards.db"
        summary = load.build(ROOT / "data" / "raw", ROOT / "docs" / "reference" / "codes.csv",
                             ROOT / "src" / "schema.sql", db,
                             ROOT / "data" / "curated" / "identifier_corrections.csv",
                             review_dir=review)
        con = sqlite3.connect(db)
        edges = {(a, b, kind): (source, reviewed) for a, b, kind, source, reviewed in con.execute(
            "SELECT from_record_id, to_record_id, type, source, reviewed FROM edges")}
        con.close()
        return summary, edges


class Decisions(unittest.TestCase):

    def test_keep_marks_the_link_reviewed(self):
        summary, edges = build_with("keep,,5685,5729,next_grade,1\n")
        self.assertEqual(edges[(5685, 5729, "next_grade")], ("structural", 1))
        self.assertEqual(summary["decisions"]["kept"], 1)

    def test_reject_leaves_the_link_out(self):
        _, edges = build_with("reject,not the same skill,5729,5773,next_grade,1\n")
        self.assertNotIn((5729, 5773, "next_grade"), edges)
        self.assertIn((5685, 5729, "next_grade"), edges)        # its neighbour is untouched

    def test_keep_on_a_candidate_adds_the_link_as_the_owners(self):
        summary, edges = build_with("keep,,301,355,builds_towards,1\n")
        self.assertEqual(edges[(301, 355, "builds_towards")], ("owner", 1))
        self.assertEqual(summary["decisions"]["added"], 1)

    def test_a_decision_without_reviewed_1_is_not_applied(self):
        summary, edges = build_with("reject,,5729,5773,next_grade,0\n")
        self.assertEqual(edges[(5729, 5773, "next_grade")], ("structural", 0))
        self.assertEqual(summary["decisions"]["pending"], 1)

    def test_blank_rows_change_nothing(self):
        summary, edges = build_with(",,5729,5773,next_grade,0\n")
        self.assertEqual(edges[(5729, 5773, "next_grade")], ("structural", 0))
        self.assertEqual(summary["decisions"],
                         {"kept": 0, "added": 0, "rejected": 0, "pending": 0})

    def test_reviewed_with_an_unknown_decision_stops_the_load(self):
        with self.assertRaises(load.LoadError):
            build_with("maybe,,5729,5773,next_grade,1\n")

    def test_keep_naming_a_record_that_does_not_exist_stops_the_load(self):
        with self.assertRaises(load.LoadError):
            build_with("keep,,301,999999,builds_towards,1\n")

    def test_confidence_on_a_kept_link_is_stored(self):
        found = confidence_after("keep,High,,5685,5729,next_grade,1\n")
        self.assertEqual(found[(5685, 5729, "next_grade")], "high")

    def test_confidence_is_optional(self):
        found = confidence_after("keep,,,5685,5729,next_grade,1\n")
        self.assertIsNone(found[(5685, 5729, "next_grade")])

    def test_confidence_on_an_accepted_candidate_is_stored(self):
        found = confidence_after("keep,low,,301,355,builds_towards,1\n")
        self.assertEqual(found[(301, 355, "builds_towards")], "low")

    def test_confidence_without_reviewed_1_is_not_applied(self):
        found = confidence_after("keep,high,,5685,5729,next_grade,0\n")
        self.assertIsNone(found[(5685, 5729, "next_grade")])

    def test_an_unknown_confidence_stops_the_load(self):
        with self.assertRaises(load.LoadError):
            confidence_after("keep,very,,5685,5729,next_grade,1\n")

    def test_the_real_sheets_load(self):
        with tempfile.TemporaryDirectory() as tmp:
            summary = load.build(ROOT / "data" / "raw", ROOT / "docs" / "reference" / "codes.csv",
                                 ROOT / "src" / "schema.sql", Path(tmp) / "standards.db",
                                 ROOT / "data" / "curated" / "identifier_corrections.csv",
                                 ROOT / "data" / "derived" / "learning_commons_edges.csv",
                                 ROOT / "data" / "derived" / "learning_commons_parents.csv",
                                 ROOT / "data" / "derived" / "learning_commons_eld_ela.csv",
                                 ROOT / "data" / "curated" / "review")
        self.assertIn("decisions", summary)


if __name__ == "__main__":
    unittest.main()
