"""
Tests for data/curated/search_terms.csv and how the loader reads it.

    python -m unittest discover tests -v

Most tests write a small file into a temporary folder; the real file is only
read, never changed.
"""
import csv
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import load  # noqa: E402

REAL = ROOT / "data" / "curated" / "search_terms.csv"
HEADER = "teacher_term,standards_term,subject,evidence,source,reviewed\n"


def read(text):
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "search_terms.csv"
        path.write_text(text, encoding="utf-8")
        return load.read_search_terms(path)


class Reading(unittest.TestCase):

    def test_a_row_is_read_tidied(self):
        rows = read(HEADER + " Regroup , Compose ,math,why,claude,0\n")
        self.assertEqual(rows, [("regroup", "compose", "math", "why", "claude", 0)])

    def test_a_blank_subject_means_any_subject(self):
        self.assertIsNone(read(HEADER + "plus,add,,why,owner,1\n")[0][2])

    def test_a_missing_file_gives_no_rows(self):
        self.assertEqual(load.read_search_terms(Path("no such file.csv")), [])

    def test_bad_rows_stop_the_load(self):
        for row in ["regroup,,math,why,claude,0",            # no standards term
                    "regroup,compose,maths,why,claude,0",    # unknown subject
                    "regroup,compose,math,why,claude,yes",   # reviewed not 0 or 1
                    "regroup,compose,math,why,,0"]:          # no source
            with self.subTest(row=row), self.assertRaises(load.LoadError):
                read(HEADER + row + "\n")

    def test_a_pair_listed_twice_stops_the_load(self):
        with self.assertRaises(load.LoadError):
            read(HEADER + "regroup,compose,math,a,claude,0\nRegroup,compose,math,b,claude,0\n")

    def test_other_columns_stop_the_load(self):
        with self.assertRaises(load.LoadError):
            read("teacher_term,standards_term\nregroup,compose\n")


class RealFile(unittest.TestCase):

    def test_it_loads_into_the_database(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "standards.db"
            summary = load.build(ROOT / "data" / "raw", ROOT / "docs" / "reference" / "codes.csv",
                                 ROOT / "src" / "schema.sql", db,
                                 ROOT / "data" / "curated" / "identifier_corrections.csv",
                                 search_terms_path=REAL)
            con = sqlite3.connect(db)
            loaded = con.execute("SELECT COUNT(*) FROM search_terms").fetchone()[0]
            con.close()
        self.assertEqual(loaded, summary["search_terms"][0])
        self.assertGreater(loaded, 0)

    def test_claudes_rows_are_unreviewed(self):
        with open(REAL, encoding="utf-8-sig", newline="") as f:
            for r in csv.DictReader(f):
                if r["source"] == "claude":
                    self.assertEqual(r["reviewed"], "0", r["teacher_term"])


if __name__ == "__main__":
    unittest.main()
