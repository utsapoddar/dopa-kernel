import sys
import tempfile
import unittest
from pathlib import Path

K = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(K))
import evaluator  # noqa: E402
import model  # noqa: E402


def command_contract(command="printf OK", *, imp=3,
                     level="independent", marker="OK"):
    verify = {"kind": "command", "command": command, "expect_exit": 0, "level": level}
    if marker is not None:
        verify["output_contains"] = marker
    return {
        "objective": "Prove the work",
        "imp": imp,
        "constraints": [],
        "requirements": [
            {"id": "proof", "text": "The verifier passes", "priority": 5, "verify": verify}
        ],
    }


class EvaluatorTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())

    def test_missing_evidence_is_not_met(self):
        state = model.start_goal(command_contract(), self.root)
        result = evaluator.evaluate(state)
        self.assertEqual(result["verdict"], "not_met")
        self.assertIn("missing", result["reason"])

    def test_failed_exact_command_receipt_is_not_met(self):
        model.start_goal(command_contract("false", marker=None), self.root)
        receipt = evaluator.verify_requirement(self.root, "proof")
        self.assertFalse(receipt["passed"])
        self.assertEqual(evaluator.evaluate(model.load_state(self.root))["verdict"], "not_met")

    def test_weak_evidence_cannot_satisfy_goal_importance(self):
        model.start_goal(command_contract(imp=5, level="held-out"), self.root)
        receipt = evaluator.verify_requirement(self.root, "proof")
        self.assertTrue(receipt["passed"])
        state = model.load_state(self.root)
        state["requirements"][0]["evidence"]["level"] = "independent"
        model.save_state(state, self.root)
        result = evaluator.evaluate(model.load_state(self.root))
        self.assertEqual(result["verdict"], "not_met")
        self.assertIn("held-out", result["reason"])

    def test_later_mutation_makes_passing_evidence_stale(self):
        model.start_goal(command_contract(), self.root)
        evaluator.verify_requirement(self.root, "proof")
        model.record_mutation(self.root, "Edit")
        result = evaluator.evaluate(model.load_state(self.root))
        self.assertEqual(result["verdict"], "not_met")
        self.assertIn("stale", result["reason"])

    def test_file_verifier_supports_non_test_goals(self):
        (self.root / "answer.txt").write_text("objective satisfied\n")
        contract = {
            "objective": "Produce a checked artifact", "imp": 2, "constraints": [],
            "requirements": [{"id": "artifact", "text": "Artifact has required content",
                              "priority": 5, "verify": {"kind": "file", "path": "answer.txt",
                              "contains": ["objective satisfied"], "level": "observed"}}],
        }
        model.start_goal(contract, self.root)
        receipt = evaluator.verify_requirement(self.root, "artifact")
        self.assertTrue(receipt["passed"])
        self.assertEqual(evaluator.evaluate(model.load_state(self.root))["verdict"], "met")

    def test_known_regression_blocks_completion(self):
        state = model.start_goal(command_contract(), self.root)
        evaluator.verify_requirement(self.root, "proof")
        state = model.load_state(self.root)
        state["known_regression"] = "Public API broke"
        model.save_state(state, self.root)
        result = evaluator.evaluate(model.load_state(self.root))
        self.assertEqual(result["verdict"], "not_met")
        self.assertIn("regression", result["reason"])

    def test_all_fresh_strong_receipts_are_met_and_can_finalize(self):
        model.start_goal(command_contract(), self.root)
        evaluator.verify_requirement(self.root, "proof")
        result = evaluator.evaluate_goal(self.root, finalize=True)
        self.assertEqual(result["verdict"], "met")
        self.assertEqual(model.load_state(self.root)["status"], "complete")

    def test_terminal_external_blocker_is_impossible(self):
        state = model.start_goal(command_contract(), self.root)
        state["terminal_blocker"] = "Required external service was permanently removed"
        model.save_state(state, self.root)
        result = evaluator.evaluate(model.load_state(self.root))
        self.assertEqual(result["verdict"], "impossible")

    def test_impossible_finalization_allows_a_replacement_goal(self):
        state = model.start_goal(command_contract(), self.root)
        state["terminal_blocker"] = "Required external service was permanently removed"
        model.save_state(state, self.root)
        result = evaluator.evaluate_goal(self.root, finalize=True)
        self.assertEqual(result["verdict"], "impossible")
        self.assertEqual(model.load_state(self.root)["status"], "impossible")
        replacement = model.start_goal(command_contract(command="true", marker=None), self.root)
        self.assertEqual(replacement["status"], "active")

    def test_contract_rejects_an_evidence_level_below_importance_floor(self):
        with self.assertRaisesRegex(ValueError, "below imp"):
            model.start_goal(command_contract(imp=5, level="independent"), self.root)

    def test_observation_without_verifier_receipt_never_counts(self):
        state = model.start_goal(command_contract(), self.root)
        state["observations"].append({"claim": "looks done", "i": "decision-changing"})
        self.assertEqual(evaluator.evaluate(state)["verdict"], "not_met")

    def test_fresh_receipt_does_not_skip_missing_action_outcome(self):
        state = model.start_goal(command_contract(), self.root)
        state["selected_action"] = {"id": "build", "verdict": "commit",
                                    "awaiting_outcome": True}
        model.save_state(state, self.root)
        evaluator.verify_requirement(self.root, "proof")
        result = evaluator.evaluate(model.load_state(self.root))
        self.assertEqual(result["verdict"], "not_met")
        self.assertIn("outcome", result["reason"])


if __name__ == "__main__":
    unittest.main()
