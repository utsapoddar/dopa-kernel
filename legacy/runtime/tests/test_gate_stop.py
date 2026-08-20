import sys, tempfile, unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import gate_stop
from kernel_state import KernelState


def state(active=True, modules_read=None, last_user_at=0, substantive=True):
    st = KernelState(active=active)
    st.modules_read = modules_read or {}
    st.last_user_at = last_user_at
    # by default the turn did real work, so the gate applies
    st.substantive_ops = [last_user_at + 1] if substantive else []
    return st


class TestStopGate(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        gate_stop.STATE_DIR = Path(self._tmp)

    def test_inert_when_kernel_not_active(self):
        self.assertIsNone(gate_stop.decide(state(active=False)))

    def test_stop_without_completion_module_is_blocked(self):
        reason = gate_stop.decide(state(modules_read={"combined.md": 1}))
        self.assertIsNotNone(reason)
        self.assertIn("K5", reason)

    def test_completion_read_before_last_user_turn_does_not_count(self):
        st = state(modules_read={"completion.md": 3}, last_user_at=10)
        self.assertIsNotNone(gate_stop.decide(st))

    def test_completion_read_after_last_user_turn_allows_stop(self):
        st = state(modules_read={"completion.md": 12}, last_user_at=10)
        self.assertIsNone(gate_stop.decide(st))

    def test_turn_with_no_substantive_work_is_not_gated(self):
        """A pure routing or conversational turn has nothing to verify."""
        st = state(modules_read={"combined.md": 1}, substantive=False)
        self.assertIsNone(gate_stop.decide(st))

    def test_turn_with_work_is_still_gated(self):
        st = state(modules_read={"combined.md": 1}, substantive=True)
        self.assertIsNotNone(gate_stop.decide(st))

    def test_work_in_an_earlier_turn_does_not_gate_this_one(self):
        st = state(modules_read={"combined.md": 1}, last_user_at=50, substantive=False)
        st.substantive_ops = [3]
        self.assertIsNone(gate_stop.decide(st))

    def test_block_count_starts_at_zero(self):
        self.assertEqual(gate_stop.block_count("s1", "p1"), 0)

    def test_bump_increments_and_persists(self):
        self.assertEqual(gate_stop.bump("s1", "p1"), 1)
        self.assertEqual(gate_stop.bump("s1", "p1"), 2)
        self.assertEqual(gate_stop.block_count("s1", "p1"), 2)

    def test_counts_are_isolated_per_prompt(self):
        gate_stop.bump("s1", "p1")
        self.assertEqual(gate_stop.block_count("s1", "p2"), 0)

    def test_max_stop_blocks_is_two(self):
        self.assertEqual(gate_stop.MAX_STOP_BLOCKS, 2)


if __name__ == "__main__":
    unittest.main()
