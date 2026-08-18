import sys, unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import gate_pretooluse as gate
from kernel_state import KernelState


def state(**kw):
    st = KernelState(active=kw.pop("active", True))
    st.modules_read = kw.pop("modules_read", {})
    st.cells = kw.pop("cells", [])
    return st


BASH_DESTRUCTIVE = {"command": "git push origin main"}
BASH_WRITING = {"command": "echo x > /tmp/z/scratchpad/notes.md"}
BASH_READ = {"command": "git status"}


REAL = {"file_path": "/Users/x/projects/app/main.py"}
SCRATCH = {"file_path": "/private/tmp/claude-501/xyz/scratchpad/note.md"}
FULL = {"combined.md": 1, "rollback.md": 2}


class TestPreToolUseGate(unittest.TestCase):
    def test_inert_when_kernel_not_active(self):
        st = state(active=False, modules_read={})
        self.assertIsNone(gate.decide(st, "Write", REAL))

    def test_non_mutating_tool_is_never_blocked(self):
        st = state(modules_read={})
        self.assertIsNone(gate.decide(st, "Read", REAL))
        self.assertIsNone(gate.decide(st, "Grep", REAL))

    def test_write_without_domain_adapter_is_blocked(self):
        reason = gate.decide(state(modules_read={}), "Write", REAL)
        self.assertIsNotNone(reason)
        self.assertIn("K2", reason)

    def test_write_without_rollback_is_blocked(self):
        reason = gate.decide(state(modules_read={"combined.md": 1}), "Write", REAL)
        self.assertIsNotNone(reason)
        self.assertIn("K4", reason)

    def test_scratch_write_does_not_need_rollback(self):
        st = state(modules_read={"combined.md": 1})
        self.assertIsNone(gate.decide(st, "Write", SCRATCH))

    def test_fully_routed_write_is_allowed(self):
        self.assertIsNone(gate.decide(state(modules_read=FULL), "Write", REAL))

    def test_outside_envelope_without_proposal_is_blocked(self):
        st = state(modules_read=FULL, cells=[(5, "C", "outside")])
        reason = gate.decide(st, "Write", REAL)
        self.assertIsNotNone(reason)
        self.assertIn("K3", reason)

    def test_outside_envelope_with_proposal_is_allowed(self):
        mods = dict(FULL, **{"proposal.md": 6})
        st = state(modules_read=mods, cells=[(5, "C", "outside")])
        self.assertIsNone(gate.decide(st, "Write", REAL))

    def test_return_to_inside_envelope_clears_the_proposal_requirement(self):
        st = state(modules_read=FULL, cells=[(5, "C", "outside"), (9, "C", "inside")])
        self.assertIsNone(gate.decide(st, "Write", REAL))

    def test_edit_is_gated_like_write(self):
        reason = gate.decide(state(modules_read={}), "Edit", REAL)
        self.assertIn("K2", reason)

    def test_destructive_bash_without_rollback_is_blocked(self):
        st = state(modules_read={"combined.md": 1})
        reason = gate.decide(st, "Bash", BASH_DESTRUCTIVE)
        self.assertIsNotNone(reason)
        self.assertIn("K4", reason)

    def test_destructive_bash_with_rollback_is_allowed(self):
        st = state(modules_read={"combined.md": 1, "rollback.md": 2})
        self.assertIsNone(gate.decide(st, "Bash", BASH_DESTRUCTIVE))

    def test_writing_bash_is_not_gated(self):
        st = state(modules_read={"combined.md": 1})
        self.assertIsNone(gate.decide(st, "Bash", BASH_WRITING))

    def test_read_only_bash_is_not_gated(self):
        st = state(modules_read={"combined.md": 1})
        self.assertIsNone(gate.decide(st, "Bash", BASH_READ))

    def test_destructive_bash_still_needs_an_adapter(self):
        reason = gate.decide(state(modules_read={}), "Bash", BASH_DESTRUCTIVE)
        self.assertIn("K2", reason)

    def test_bash_is_inert_when_kernel_inactive(self):
        st = state(active=False, modules_read={})
        self.assertIsNone(gate.decide(st, "Bash", BASH_DESTRUCTIVE))

    def test_scratch_detection(self):
        self.assertTrue(gate.is_scratch("/tmp/foo"))
        self.assertTrue(gate.is_scratch("/private/tmp/bar"))
        self.assertTrue(gate.is_scratch("/Users/x/scratchpad/baz.md"))
        self.assertFalse(gate.is_scratch("/Users/x/projects/app/main.py"))


if __name__ == "__main__":
    unittest.main()
