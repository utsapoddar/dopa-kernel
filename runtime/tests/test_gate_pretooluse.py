import sys, unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import gate_pretooluse as gate
from kernel_state import KernelState


def state(**kw):
    st = KernelState(active=kw.pop("active", True))
    st.modules_read = kw.pop("modules_read", {})
    st.cells = kw.pop("cells", [])
    # Stakes are declared by default so each test below exercises the gate it
    # names rather than tripping K1 first; the stakes gate has its own tests.
    st.imps = kw.pop("imps", [(0, 3)])
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


class TestStakesGate(unittest.TestCase):
    def test_write_without_declared_stakes_is_blocked(self):
        reason = gate.decide(state(modules_read=FULL, imps=[]), "Write", REAL)
        self.assertIsNotNone(reason)
        self.assertIn("K1", reason)
        self.assertIn("imp", reason)

    def test_stakes_gate_precedes_the_adapter_gate(self):
        reason = gate.decide(state(modules_read={}, imps=[]), "Write", REAL)
        self.assertIn("K1", reason)
        self.assertNotIn("K2", reason)

    def test_the_declaring_write_is_not_blocked_by_its_own_gate(self):
        st = state(modules_read=FULL, imps=[])
        payload = {"file_path": "/tmp/z/scratchpad/notes.md",
                   "content": "envelope\nimp: 4\ndue: 2026-09-08\n"}
        self.assertIsNone(gate.decide(st, "Write", payload))

    def test_declaring_via_bash_heredoc_also_clears_the_gate(self):
        st = state(modules_read=FULL, imps=[])
        payload = {"command": "cat >> notes.md <<'EOF'\nimp: 2\nEOF"}
        self.assertIsNone(gate.decide(st, "Bash", payload))

    def test_menu_line_from_the_kernel_text_does_not_count_as_declaring(self):
        st = state(modules_read=FULL, imps=[])
        payload = {"file_path": "/tmp/z/scratchpad/n.md",
                   "content": "    imp: 1 | 2 | 3 | 4 | 5\n"}
        self.assertIsNotNone(gate.decide(st, "Bash", {"command": "rm -rf /tmp/z"}))
        self.assertIsNotNone(gate.decide(st, "Write", payload))

    def test_stakes_gate_is_inert_when_kernel_not_active(self):
        st = state(active=False, modules_read={}, imps=[])
        self.assertIsNone(gate.decide(st, "Write", REAL))

    def test_non_mutating_tool_never_trips_the_stakes_gate(self):
        st = state(modules_read={}, imps=[])
        self.assertIsNone(gate.decide(st, "Read", REAL))
