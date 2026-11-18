"""
Tests for scripts/make_prototype_data.py: the data the prototype page reads
must be the database's contents, whole and unchanged.

    python -m unittest discover tests -v
"""
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import load                   # noqa: E402
import make_prototype_data    # noqa: E402

DERIVED = ROOT / "data" / "derived"


class Export(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        db = Path(cls.tmp.name) / "standards.db"
        load.build(ROOT / "data" / "raw", ROOT / "docs" / "reference" / "codes.csv",
                   ROOT / "src" / "schema.sql", db,
                   ROOT / "data" / "curated" / "identifier_corrections.csv",
                   DERIVED / "learning_commons_edges.csv", DERIVED / "learning_commons_parents.csv",
                   DERIVED / "learning_commons_eld_ela.csv", components_dir=DERIVED,
                   search_terms_path=ROOT / "data" / "curated" / "search_terms.csv")
        cls.con = sqlite3.connect(db)
        cls.con.row_factory = sqlite3.Row
        cls.data = make_prototype_data.export(cls.con)

    @classmethod
    def tearDownClass(cls):
        cls.con.close()
        cls.tmp.cleanup()

    def count(self, table):
        return self.con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]

    def test_every_row_is_exported(self):
        self.assertEqual(len(self.data["standards"]), self.count("standards"))
        self.assertEqual(len(self.data["edges"]), self.count("edges"))
        self.assertEqual(len(self.data["eld_ela"]), self.count("eld_ela_links"))
        self.assertEqual(len(self.data["components"]), self.count("learning_components"))
        self.assertEqual(len(self.data["component_links"]), self.count("component_links"))
        self.assertEqual(len(self.data["search_terms"]), self.count("search_terms"))
        self.assertGreater(len(self.data["search_terms"]), 0)

    def test_every_link_names_exported_standards(self):
        ids = {s["id"] for s in self.data["standards"]}
        for edge in self.data["edges"]:
            self.assertIn(edge[0], ids)
            self.assertIn(edge[1], ids)
        for row in self.data["eld_ela"]:
            self.assertIn(row[3], ids)
        for row in self.data["component_links"]:
            self.assertIn(row[0], ids)
            self.assertIn(row[2], self.data["components"])

    def test_record_ids_and_identifiers_are_as_in_the_database(self):
        by_id = {s["id"]: s for s in self.data["standards"]}
        self.assertEqual(by_id[378]["identifier"], "4.NF.3.a")
        self.assertEqual(by_id[378]["url"], "https://www2.cde.ca.gov/cacs/id/web/378")
        parent = by_id[by_id[378]["parent"]]
        self.assertEqual(parent["identifier"], "4.NF.3")
        self.assertIsNone(parent["url"])            # CDE has no record for it
        self.assertEqual([letter for letter, _ in by_id[5773]["subs"]], list("abcde"))   # L.5.1

    def test_reviewed_flags_are_copied_not_set(self):
        self.assertEqual({e[5] for e in self.data["edges"]}, {0})
        self.assertEqual({e[6] for e in self.data["edges"]}, {None})     # no confidence without a review

    def test_it_can_be_written_as_json(self):
        self.assertIsInstance(json.dumps(self.data, ensure_ascii=False), str)


if __name__ == "__main__":
    unittest.main()
