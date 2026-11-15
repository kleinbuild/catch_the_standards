"""
Tests for the small functions in scripts/join_learning_commons.py.

    python -m unittest discover tests -v

These need no Learning Commons files. The pairing itself is checked by running
the script and reading its report.
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import join_learning_commons as join  # noqa: E402


class CodeRewrite(unittest.TestCase):

    def test_k8_drops_the_cluster_letter(self):
        self.assertEqual(join.cde_form("3.NF.A.2", ""), "3.NF.2")
        self.assertEqual(join.cde_form("K.CC.B.4.a", ""), "K.CC.4.a")
        self.assertEqual(join.cde_form("5.OA.A.2.1", ""), "5.OA.2.1")

    def test_one_letter_domain_is_not_mistaken_for_a_cluster(self):
        # In K.G.B.6 the domain (G) and the cluster (B) are both one letter.
        self.assertEqual(join.cde_form("K.G.B.6", ""), "K.G.6")
        self.assertEqual(join.cde_form("HSG-C.A.2", ""), "G-C.2")

    def test_high_school(self):
        self.assertEqual(join.cde_form("HSA-CED.A.1", "Algebra I"), "A-CED.1")
        self.assertEqual(join.cde_form("HSF-BF.B.4.a", ""), "F-BF.4.a")

    def test_california_additions_written_with_a_dot(self):
        self.assertEqual(join.cde_form("HSF.LE.A.4.1", "Algebra II"), "F-LE.4.1")
        self.assertEqual(join.cde_form("HSG.GMD.5", "Geometry"), "G-GMD.5")   # no cluster letter

    def test_course_numbered_standards(self):
        self.assertEqual(join.cde_form("17.0", "Calculus"), "Calculus.17.0")
        self.assertEqual(join.cde_form("9.0", "Statistics and Probability (AP)"), "AP-Prob&Stats.9.0")

    def test_codes_with_nothing_to_drop_are_left_alone(self):
        for code in ("2.NBT.7.1", "MP1", "3.NF.A"):
            self.assertEqual(join.cde_form(code, ""), code)


class PathwayPairs(unittest.TestCase):
    """Record IDs here are made up; the letters stand for courses."""

    def test_k8_to_k8(self):
        self.assertEqual(join.pathway_pairs({1: ""}, {2: ""}), {(1, 2)})

    def test_k8_links_to_every_course_copy(self):
        self.assertEqual(join.pathway_pairs({1: ""}, {2: "Algebra I", 3: "Math I"}),
                         {(1, 2), (1, 3)})

    def test_same_course_copies_are_joined(self):
        earlier = {1: "Algebra I", 2: "Algebra II", 3: "Math I"}
        later = {4: "Algebra I", 5: "Algebra II", 6: "Math I"}
        self.assertEqual(join.pathway_pairs(earlier, later), {(1, 4), (2, 5), (3, 6)})

    def test_nearest_earlier_course_in_the_pathway(self):
        earlier = {1: "Algebra I", 2: "Math I"}
        later = {3: "Algebra II", 4: "Math III"}
        self.assertEqual(join.pathway_pairs(earlier, later), {(1, 3), (2, 4)})

    def test_never_across_pathways(self):
        self.assertEqual(join.pathway_pairs({1: "Algebra I"}, {2: "Math III"}), set())

    def test_never_from_a_later_course(self):
        self.assertEqual(join.pathway_pairs({1: "Algebra II"}, {2: "Algebra I"}), set())

    def test_statistics_course_follows_either_pathway(self):
        earlier = {1: "Algebra I", 2: "Math I"}
        self.assertEqual(join.pathway_pairs(earlier, {3: "Statistics and Probability"}),
                         {(1, 3), (2, 3)})


class EldNotes(unittest.TestCase):

    def test_ranges_and_lists(self):
        found, unread = join.parse_note("W.4.4\u20135; SL.4.4, 6; L.4.1, 3, 5\u20136")
        self.assertEqual([f[:3] for f in found],
                         [("W", "4", "4"), ("W", "4", "5"), ("SL", "4", "4"), ("SL", "4", "6"),
                          ("L", "4", "1"), ("L", "4", "3"), ("L", "4", "5"), ("L", "4", "6")])
        self.assertEqual(unread, [])

    def test_grade_bands(self):
        found, _ = join.parse_note("RL.9\u201310.1, 7\u20139")
        self.assertEqual([f[:3] for f in found],
                         [("RL", "9-10", "1"), ("RL", "9-10", "7"), ("RL", "9-10", "8"),
                          ("RL", "9-10", "9")])

    def test_text_that_is_not_a_list_is_reported(self):
        self.assertEqual(join.parse_note("Not applicable at grade 1"),
                         ([], ["Not applicable at grade 1"]))


class PlainMath(unittest.TestCase):

    def test_fractions(self):
        self.assertEqual(join.plain_math("a fraction $\\frac{a}{b}$ with a > 1 as a sum of "
                                         "fractions $\\frac{1}{b}$."),
                         "a fraction a/b with a > 1 as a sum of fractions 1/b.")

    def test_ordinary_text_is_unchanged(self):
        self.assertEqual(join.plain_math("Relate area to multiplication."),
                         "Relate area to multiplication.")


class TextCheck(unittest.TestCase):

    def test_same_despite_dashes_and_quotes(self):
        verdict, _ = join.text_check("ten ones—called a “ten.”", 'ten ones - called a "ten."')
        self.assertEqual(verdict, "same")

    def test_contained(self):
        # CDE puts the parent's sentence in front of a math sub-item.
        cde = "Understand the relationship between numbers and quantities. Count objects."
        self.assertEqual(join.text_check(cde, "Count objects.")[0], "one contains the other")

    def test_differs(self):
        self.assertEqual(join.text_check("Use definite integrals.", "Compute integrals by hand.")[0],
                         "differs")


if __name__ == "__main__":
    unittest.main()
