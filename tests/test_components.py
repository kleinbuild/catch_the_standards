"""
Tests for learning components (data/derived/learning_commons_components.csv and
learning_commons_component_links.csv).

    python -m unittest discover tests -v

The two files are large and may not be on this machine; without them these
tests are skipped. `python scripts/join_learning_commons.py` writes them.
"""
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import load  # noqa: E402

DERIVED = ROOT / "data" / "derived"
HAVE_FILES = ((DERIVED / "learning_commons_components.csv").exists()
              and (DERIVED / "learning_commons_component_links.csv").exists())


@unittest.skipUnless(HAVE_FILES, "learning component files are not in data/derived/")
class Components(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        db = Path(cls.tmp.name) / "standards.db"
        cls.summary = load.build(
            ROOT / "data" / "raw", ROOT / "docs" / "reference" / "codes.csv",
            ROOT / "src" / "schema.sql", db,
            ROOT / "data" / "curated" / "identifier_corrections.csv",
            parents_path=DERIVED / "learning_commons_parents.csv", components_dir=DERIVED)
        cls.con = sqlite3.connect(db)

    @classmethod
    def tearDownClass(cls):
        cls.con.close()
        cls.tmp.cleanup()

    def q(self, sql, *args):
        return self.con.execute(sql, args).fetchall()

    def test_components_of_a_math_sub_item_record(self):
        texts = [t for (t,) in self.q(
            "SELECT c.text FROM component_links l JOIN learning_components c USING (component_id) "
            "JOIN standards s USING (record_id) WHERE s.identifier = '4.NF.3.a' ORDER BY 1")]
        self.assertEqual(texts, [
            "Recognize addition of fractions as joining parts referring to the same whole",
            "Recognize subtraction of fractions as separating parts referring to the same whole"])

    def test_ela_components_land_on_the_lettered_sub_item(self):
        letters = {l for (l,) in self.q(
            "SELECT DISTINCT l.letter FROM component_links l JOIN standards s USING (record_id) "
            "WHERE s.identifier = 'L.1.1'")}
        self.assertIn("e", letters)
        # Every lettered attachment names a sub-item the loader really split out.
        self.assertEqual(self.q(
            "SELECT COUNT(*) FROM component_links l WHERE l.letter <> '' AND NOT EXISTS "
            "(SELECT 1 FROM sub_items i WHERE i.record_id = l.record_id AND i.letter = l.letter)"),
            [(0,)])

    def test_ela_components_are_k_to_2_only(self):
        self.assertEqual(self.q(
            "SELECT MAX(s.grade_max) FROM component_links l JOIN standards s USING (record_id) "
            "WHERE s.subject = 'ela'"), [(2,)])

    def test_every_component_is_attached_and_none_is_reviewed(self):
        self.assertEqual(self.q(
            "SELECT COUNT(*) FROM learning_components c WHERE NOT EXISTS "
            "(SELECT 1 FROM component_links l WHERE l.component_id = c.component_id)"), [(0,)])
        self.assertEqual(self.q("SELECT COUNT(*) FROM component_links WHERE reviewed <> 0"), [(0,)])

    def test_a_course_free_attachment_reaches_each_course_copy(self):
        # A-CED.1 is five records; Learning Commons attaches its components to one copy.
        counts = self.q("SELECT s.record_id, COUNT(*) FROM component_links l JOIN standards s "
                        "USING (record_id) WHERE s.identifier = 'A-CED.1' GROUP BY 1")
        self.assertEqual(len(counts), 5)
        self.assertEqual(len({n for _, n in counts}), 1)


class WithoutTheFiles(unittest.TestCase):

    def test_the_database_builds_with_no_components(self):
        with tempfile.TemporaryDirectory() as tmp:
            summary = load.build(ROOT / "data" / "raw", ROOT / "docs" / "reference" / "codes.csv",
                                 ROOT / "src" / "schema.sql", Path(tmp) / "standards.db",
                                 components_dir=Path(tmp))
        self.assertEqual(summary["components"], (0, 0))


if __name__ == "__main__":
    unittest.main()
