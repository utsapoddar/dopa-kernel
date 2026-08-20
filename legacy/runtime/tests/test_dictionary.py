import sys, unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import dictionary as d

INSIDE_ADV_NONE = ("inside", "advanced", "none")
INSIDE_NEU_CHANGING = ("inside", "neutral", "decision-changing")
INSIDE_NEU_NONE = ("inside", "neutral", "none")
INSIDE_REG_CHANGING = ("inside", "regressed", "decision-changing")
OUTSIDE_ADV_CHANGING = ("outside", "advanced", "decision-changing")


class TestDictionary(unittest.TestCase):
    def test_frame_has_exactly_eighteen_cells(self):
        self.assertEqual(len(d.CELLS), 18)
        self.assertEqual(len(set(d.CELLS)), 18)

    def test_legality(self):
        self.assertTrue(d.is_legal(INSIDE_ADV_NONE))
        self.assertFalse(d.is_legal(("inside", "advanced", "lots")))
        self.assertFalse(d.is_legal(("sideways", "advanced", "none")))
        self.assertFalse(d.is_legal(("inside", "advanced")))

    def test_outside_envelope_is_ineligible_at_any_position(self):
        self.assertFalse(d.is_eligible(OUTSIDE_ADV_CHANGING))
        self.assertTrue(d.is_eligible(INSIDE_NEU_NONE))

    def test_lexicographic_gate_dominates_both_axes(self):
        self.assertEqual(d.compare(INSIDE_NEU_NONE, OUTSIDE_ADV_CHANGING), "a>b")

    def test_pareto_dominance(self):
        self.assertEqual(d.compare(INSIDE_ADV_NONE, INSIDE_NEU_NONE), "a>b")
        self.assertEqual(d.compare(INSIDE_NEU_NONE, INSIDE_ADV_NONE), "b>a")

    def test_declared_incomparable_pair_is_not_resolved(self):
        self.assertEqual(d.compare(INSIDE_ADV_NONE, INSIDE_NEU_CHANGING), "incomparable")
        self.assertEqual(d.compare(INSIDE_NEU_CHANGING, INSIDE_ADV_NONE), "incomparable")

    def test_identical_cells_are_equal(self):
        self.assertEqual(d.compare(INSIDE_ADV_NONE, INSIDE_ADV_NONE), "equal")

    def test_regression_floor_blocks_trading_progress_for_information(self):
        self.assertTrue(d.violates_regression_floor(INSIDE_REG_CHANGING, INSIDE_NEU_NONE))

    def test_regression_floor_allows_non_regressing_choice(self):
        self.assertFalse(d.violates_regression_floor(INSIDE_NEU_CHANGING, INSIDE_NEU_NONE))

    def test_illegal_cells_raise(self):
        with self.assertRaises(ValueError):
            d.compare(("inside", "advanced", "lots"), INSIDE_NEU_NONE)


if __name__ == "__main__":
    unittest.main()
