"""
Tests for src/lookup.py.

    python -m unittest discover tests -v
"""
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import load    # noqa: E402
import lookup  # noqa: E402


class Lookup(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        db = Path(cls.tmp.name) / "standards.db"
        load.build(ROOT / "data" / "raw", ROOT / "docs" / "reference" / "codes.csv",
                   ROOT / "src" / "schema.sql", db,
                   ROOT / "data" / "curated" / "identifier_corrections.csv")
        cls.con = sqlite3.connect(db)
        cls.con.row_factory = sqlite3.Row

    @classmethod
    def tearDownClass(cls):
        cls.con.close()
        cls.tmp.cleanup()

    def identifiers(self, rows):
        return [r["identifier"] for r in rows]

    def test_find_by_identifier(self):
        rows, letter = lookup.find_records(self.con, "L.5.1")
        self.assertEqual((self.identifiers(rows), letter), (["L.5.1"], None))

    def test_find_is_not_fussy_about_dashes_or_case(self):
        rows, _ = lookup.find_records(self.con, "rh.6-8.1")           # CDE writes RH.6–8.1
        self.assertEqual(self.identifiers(rows), ["RH.6–8.1"])

    def test_find_ela_sub_item(self):
        rows, letter = lookup.find_records(self.con, "L.5.1b")
        self.assertEqual((self.identifiers(rows), letter), (["L.5.1"], "b"))
        self.assertEqual(lookup.find_records(self.con, "L.5.1z"), ([], None))

    def test_find_through_a_correction(self):
        rows, _ = lookup.find_records(self.con, "RL.2.2")
        self.assertEqual(self.identifiers(rows), ["RL.2..2"])

    def test_one_identifier_can_be_several_records(self):
        rows, _ = lookup.find_records(self.con, "A-CED.1")
        self.assertEqual(len(rows), 5)

    def test_walk_back(self):
        start = lookup.find_records(self.con, "L.5.1")[0][0]["record_id"]
        found, more = lookup.walk_back(self.con, start, 2)
        names = [(steps, self.con.execute("SELECT identifier FROM standards WHERE record_id = ?",
                                          (rid,)).fetchone()[0]) for steps, rid, *_ in found]
        self.assertEqual(names, [(1, "L.4.1"), (2, "L.3.1")])
        self.assertTrue(more)                       # L.2.1 and below are still to come
        found, more = lookup.walk_back(self.con, start, 20)
        self.assertEqual(len(found), 5)             # L.4.1 down to L.K.1
        self.assertFalse(more)


if __name__ == "__main__":
    unittest.main()
