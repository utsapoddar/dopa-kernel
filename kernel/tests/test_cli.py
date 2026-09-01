import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

K = Path(__file__).resolve().parents[1]
CLI = K / "decide.py"


def goal():
    return {
        "objective": "Create the artifact", "imp": 2, "constraints": [],
        "requirements": [{"id": "artifact", "text": "Artifact is correct", "priority": 5,
                          "verify": {"kind": "file", "path": "artifact.txt",
                                     "contains": ["done"], "level": "observed"}}],
    }


def candidates():
    return {"candidates": [{
        "id": "write", "requirement_id": "artifact", "what": "Write the artifact",
        "in_frame": True, "expected_r": "advanced", "expected_i": "none",
        "cost": 1, "confidence": 5, "failure_recoverable": True,
        "uncertainty_reducible": False, "decision_critical_uncertainty": False,
        "restores_regression": False,
    }]}


class CLITest(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        (self.root / "goal.json").write_text(json.dumps(goal()))
        (self.root / "candidates.json").write_text(json.dumps(candidates()))

    def run_cli(self, *args):
        return subprocess.run([sys.executable, str(CLI), *args], cwd=self.root,
                              capture_output=True, text=True)

    def test_full_cli_lifecycle_uses_structured_state(self):
        self.assertEqual(self.run_cli("start", "goal.json").returncode, 0)
        selection = self.run_cli("select", "candidates.json")
        self.assertEqual(selection.returncode, 0, selection.stderr)
        self.assertIn("commit: write", selection.stdout)

        before = self.run_cli("evaluate")
        self.assertEqual(before.returncode, 1)
        self.assertIn("not_met", before.stdout)

        (self.root / "artifact.txt").write_text("done\n")
        receipt = self.run_cli("verify", "artifact")
        self.assertEqual(receipt.returncode, 0, receipt.stderr)
        self.assertIn('"passed": true', receipt.stdout)

        after = self.run_cli("evaluate")
        self.assertEqual(after.returncode, 0, after.stderr)
        self.assertIn("met", after.stdout)
        state = json.loads((self.root / ".dopa/goal.json").read_text())
        self.assertEqual(state["status"], "complete")

    def test_status_reports_objective_and_generation(self):
        self.run_cli("start", "goal.json")
        result = self.run_cli("status")
        self.assertEqual(result.returncode, 0)
        status = json.loads(result.stdout)
        self.assertEqual(status["objective"], "Create the artifact")
        self.assertEqual(status["mutation_generation"], 0)

    def test_unknown_requirement_verifier_is_refused(self):
        self.run_cli("start", "goal.json")
        result = self.run_cli("verify", "invented")
        self.assertEqual(result.returncode, 64)
        self.assertIn("unknown requirement", result.stderr)

    def test_structured_outcome_records_progress_information_and_surprise(self):
        self.run_cli("start", "goal.json")
        self.run_cli("select", "candidates.json")
        (self.root / "outcome.json").write_text(json.dumps({
            "delta": "as", "r": "advanced", "i": "decision-constraining",
            "note": "artifact moved toward done",
        }))
        result = self.run_cli("outcome", "outcome.json")
        self.assertEqual(result.returncode, 0, result.stderr)
        state = json.loads((self.root / ".dopa/goal.json").read_text())
        self.assertEqual(state["attempts"][-1]["r"], "advanced")
        self.assertEqual(state["attempts"][-1]["i"], "decision-constraining")

    def test_external_terminal_blocker_has_a_supported_transition(self):
        self.run_cli("start", "goal.json")
        (self.root / "blocker.json").write_text(json.dumps({
            "reason": "The required API was permanently retired",
            "evidence": "Provider deprecation notice",
        }))
        result = self.run_cli("block", "blocker.json")
        self.assertEqual(result.returncode, 0, result.stderr)
        evaluated = self.run_cli("evaluate")
        self.assertEqual(evaluated.returncode, 3)
        self.assertEqual(json.loads((self.root / ".dopa/goal.json").read_text())["status"],
                         "impossible")


if __name__ == "__main__":
    unittest.main()
