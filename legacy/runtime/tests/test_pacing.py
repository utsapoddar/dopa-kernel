import math, sys, unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pacing


class TestPacing(unittest.TestCase):
    def test_average_reward_rate(self):
        self.assertEqual(pacing.average_reward_rate(6, 120.0), 0.05)

    def test_zero_elapsed_gives_zero_rate(self):
        self.assertEqual(pacing.average_reward_rate(3, 0.0), 0.0)

    def test_optimal_latency_matches_eq4(self):
        # tau* = sqrt(C_v / Rbar); C_v=1, Rbar=0.25 -> 2.0
        self.assertAlmostEqual(pacing.optimal_latency(0.25, 1.0), 2.0)

    def test_higher_reward_rate_shortens_latency(self):
        self.assertLess(pacing.optimal_latency(1.0), pacing.optimal_latency(0.1))

    def test_zero_reward_rate_gives_infinite_latency(self):
        self.assertEqual(pacing.optimal_latency(0.0), math.inf)

    def test_nonpositive_vigor_cost_raises(self):
        with self.assertRaises(ValueError):
            pacing.optimal_latency(1.0, 0.0)


class TestStakesAxes(unittest.TestCase):
    def test_urgency_bands_match_the_tracker(self):
        self.assertEqual(pacing.urgency(-1), 100)
        self.assertEqual(pacing.urgency(3), 95)
        self.assertEqual(pacing.urgency(7), 85)
        self.assertEqual(pacing.urgency(14), 70)
        self.assertEqual(pacing.urgency(30), 50)
        self.assertEqual(pacing.urgency(60), 30)
        self.assertEqual(pacing.urgency(90), 15)
        self.assertEqual(pacing.urgency(400), 5)

    def test_no_deadline_is_unpaced_not_slow(self):
        self.assertEqual(pacing.urgency(None), 0)

    def test_urgency_is_monotone_non_increasing_in_days_left(self):
        values = [pacing.urgency(d) for d in range(-1, 200)]
        self.assertEqual(values, sorted(values, reverse=True))

    def test_evidence_floor_rises_with_importance(self):
        self.assertEqual(pacing.evidence_floor(1), "observed")
        self.assertEqual(pacing.evidence_floor(3), "not-hand-fit")
        self.assertEqual(pacing.evidence_floor(5), "independent-or-held-out")

    def test_unknown_importance_falls_back_to_the_strictest_floor(self):
        self.assertEqual(pacing.evidence_floor(99), "independent-or-held-out")

    def test_the_two_axes_are_never_combined(self):
        # The absence of a combine()/score() is the design, not an omission.
        for name in ("combine", "score", "priority", "stake_score"):
            self.assertFalse(hasattr(pacing, name), f"pacing must not expose {name}()")


if __name__ == "__main__":
    unittest.main()
