import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

K = Path(__file__).resolve().parents[1]
CLI = K / "decide.py"
PRE = K / "gate_decide.py"


def action(cid, requirement):
    return {
        "id": cid, "requirement_id": requirement, "what": cid, "in_frame": True,
        "expected_r": "advanced", "expected_i": "none", "cost": 1, "confidence": 5,
        "failure_recoverable": True, "uncertainty_reducible": False,
        "decision_critical_uncertainty": False, "restores_regression": False,
    }


class SemanticLoopIntegrationTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.trace = self.root / "trace.jsonl"
        self.trace.write_text(json.dumps({"message": {"content": [
            {"type": "tool_use", "name": "Skill", "input": {"skill": "dopa-kernel"}}
        ]}}) + "\n")
        self.goal = {
            "objective": "Build and document the artifact", "imp": 2, "constraints": [],
            "requirements": [
                {"id": "artifact", "text": "Artifact exists", "priority": 5,
                 "verify": {"kind": "file", "path": "artifact.txt",
                            "contains": ["built"], "level": "observed"}},
                {"id": "docs", "text": "Documentation exists", "priority": 4,
                 "verify": {"kind": "file", "path": "docs.txt",
                            "contains": ["documented"], "level": "observed"}},
            ],
        }

    def cli(self, *args):
        return subprocess.run([sys.executable, str(CLI), *args], cwd=self.root,
                              capture_output=True, text=True)

    def write_json(self, name, value):
        path = self.root / name
        path.write_text(json.dumps(value))
        return name

    def authorize_write(self, name):
        payload = {"transcript_path": str(self.trace), "cwd": str(self.root),
                   "tool_name": "Write", "tool_input": {"file_path": str(self.root / name)}}
        return subprocess.run([sys.executable, str(PRE)], input=json.dumps(payload),
                              capture_output=True, text=True)

    def test_full_loop_reverifies_evidence_staled_by_later_work(self):
        self.assertEqual(self.cli("start", self.write_json("goal.json", self.goal)).returncode, 0)

        self.cli("select", self.write_json("artifact-candidates.json",
                                           {"candidates": [action("build", "artifact")]}))
        self.assertEqual(self.authorize_write("artifact.txt").returncode, 0)
        (self.root / "artifact.txt").write_text("built\n")
        self.cli("outcome", self.write_json("artifact-outcome.json", {
            "delta": "as", "r": "advanced", "i": "decision-constraining"}))
        self.assertEqual(self.cli("verify", "artifact").returncode, 0)

        self.cli("select", self.write_json("docs-candidates.json",
                                           {"candidates": [action("document", "docs")]}))
        self.assertEqual(self.authorize_write("docs.txt").returncode, 0)
        (self.root / "docs.txt").write_text("documented\n")
        self.cli("outcome", self.write_json("docs-outcome.json", {
            "delta": "as", "r": "advanced", "i": "none"}))
        self.assertEqual(self.cli("verify", "docs").returncode, 0)

        stale = self.cli("evaluate")
        self.assertEqual(stale.returncode, 1)
        self.assertIn("stale evidence for artifact", stale.stdout)
        self.assertEqual(self.cli("verify", "artifact").returncode, 0)
        self.assertEqual(self.cli("evaluate").returncode, 0)

    def test_completed_goal_replacement_starts_with_isolated_history(self):
        self.cli("start", self.write_json("goal.json", self.goal))
        # Satisfy both frozen verifiers without claiming how the files were produced.
        (self.root / "artifact.txt").write_text("built\n")
        (self.root / "docs.txt").write_text("documented\n")
        self.cli("verify", "artifact")
        self.cli("verify", "docs")
        self.assertEqual(self.cli("evaluate").returncode, 0)

        replacement = dict(self.goal, objective="A genuinely different goal")
        result = self.cli("start", self.write_json("replacement.json", replacement))
        self.assertEqual(result.returncode, 0, result.stderr)
        state = json.loads((self.root / ".dopa/goal.json").read_text())
        self.assertEqual(state["attempts"], [])
        self.assertEqual(state["closed_paths"], [])
        self.assertEqual(state["mutation_generation"], 0)


if __name__ == "__main__":
    unittest.main()
