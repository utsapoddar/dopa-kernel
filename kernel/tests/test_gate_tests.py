import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

K = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(K))
import evaluator  # noqa: E402
import model  # noqa: E402

GATE = K / "gate_tests.py"


def contract():
    return {
        "objective": "Finish from evidence", "imp": 2, "constraints": [],
        "requirements": [{"id": "artifact", "text": "Artifact is done", "priority": 5,
                          "verify": {"kind": "file", "path": "artifact.txt",
                                     "contains": ["done"], "level": "observed"}}],
    }


class CompletionGateTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.trace = self.root / "trace.jsonl"
        self.trace.write_text(json.dumps({"message": {"role": "assistant", "content": [
            {"type": "tool_use", "name": "Skill", "input": {"skill": "dopa-kernel"}}
        ]}}) + "\n")

    def gate(self, *, active=True):
        payload = {"cwd": str(self.root),
                   "transcript_path": str(self.trace) if active else str(self.root / "missing")}
        return subprocess.run([sys.executable, str(GATE)], input=json.dumps(payload),
                              capture_output=True, text=True)

    def start(self):
        return model.start_goal(contract(), self.root)

    def test_active_kernel_without_goal_contract_blocks(self):
        result = self.gate()
        self.assertEqual(result.returncode, 2)
        self.assertIn("no goal", result.stderr)

    def test_missing_receipt_blocks_even_without_a_test_runner(self):
        self.start()
        result = self.gate()
        self.assertEqual(result.returncode, 2)
        self.assertIn("missing evidence", result.stderr)

    def test_fake_passing_summary_does_not_authorize_completion(self):
        self.start()
        with self.trace.open("a") as stream:
            stream.write(json.dumps({"message": {"content": [
                {"type": "tool_use", "name": "Bash", "id": "x",
                 "input": {"command": "echo '5 passed' # pytest"}},
                {"type": "tool_result", "tool_use_id": "x", "content": "5 passed"},
            ]}}) + "\n")
        self.assertEqual(self.gate().returncode, 2)

    def test_fresh_receipt_allows_stop_and_finalizes_goal(self):
        self.start()
        (self.root / "artifact.txt").write_text("done\n")
        evaluator.verify_requirement(self.root, "artifact")
        result = self.gate()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(model.load_state(self.root)["status"], "complete")

    def test_passing_receipt_then_edit_is_stale_and_blocks(self):
        self.start()
        (self.root / "artifact.txt").write_text("done\n")
        evaluator.verify_requirement(self.root, "artifact")
        model.record_mutation(self.root, "Edit")
        result = self.gate()
        self.assertEqual(result.returncode, 2)
        self.assertIn("stale evidence", result.stderr)

    def test_repeated_blocks_never_age_into_permission(self):
        self.start()
        for _ in range(4):
            self.assertEqual(self.gate().returncode, 2)

    def test_terminal_impossibility_allows_honest_stop(self):
        state = self.start()
        state["terminal_blocker"] = "Required external system no longer exists"
        model.save_state(state, self.root)
        self.assertEqual(self.gate().returncode, 0)
        self.assertEqual(model.load_state(self.root)["status"], "impossible")

    def test_inert_when_kernel_is_not_active(self):
        self.assertEqual(self.gate(active=False).returncode, 0)


if __name__ == "__main__":
    unittest.main()
