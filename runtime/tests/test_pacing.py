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


if __name__ == "__main__":
    unittest.main()
