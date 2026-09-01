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
        model.start_goal(command_contract(), self.root)
        (self.root / "provider-notice.txt").write_text("service permanently removed")
        evaluator.record_terminal_blocker(self.root, {
            "reason": "Required external service was permanently removed",
            "evidence": {"kind": "file", "path": "provider-notice.txt",
                         "contains": ["permanently removed"]},
        })
        result = evaluator.evaluate(model.load_state(self.root))
        self.assertEqual(result["verdict"], "impossible")

    def test_impossible_finalization_allows_a_replacement_goal(self):
        model.start_goal(command_contract(), self.root)
        (self.root / "provider-notice.txt").write_text("service permanently removed")
        evaluator.record_terminal_blocker(self.root, {
            "reason": "Required external service was permanently removed",
            "evidence": {"kind": "file", "path": "provider-notice.txt",
                         "contains": ["permanently removed"]},
        })
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

    def test_forged_receipt_cannot_finalize_without_the_artifact(self):
        contract = {
            "objective": "Produce a checked artifact", "imp": 2, "constraints": [],
            "requirements": [{"id": "artifact", "text": "Artifact exists", "priority": 5,
                              "verify": {"kind": "file", "path": "missing.txt",
                                         "contains": ["done"], "level": "observed"}}],
        }
        state = model.start_goal(contract, self.root)
        verify = state["requirements"][0]["verify"]
        state["requirements"][0]["evidence"] = {
            "requirement_id": "artifact",
            "verifier_id": evaluator._verifier_id(verify),
            "passed": True,
            "level": "observed",
            "generation": 0,
            "observed_at": model.now(),
            "output_digest": "forged",
            "summary": "forged",
        }
        model.save_state(state, self.root)

        result = evaluator.evaluate_goal(self.root, finalize=True)

        self.assertEqual(result["verdict"], "not_met")
        self.assertEqual(model.load_state(self.root)["status"], "active")

    def test_mutating_test_verifier_fails_and_advances_generation(self):
        (self.root / "a.txt").write_text("good")
        tests = self.root / "verifier_tests"
        tests.mkdir()
        (tests / "test_mutate.py").write_text(
            "import unittest\n"
            "from pathlib import Path\n"
            "class T(unittest.TestCase):\n"
            "    def test_mutate(self):\n"
            "        Path('a.txt').write_text('bad')\n"
        )
        contract = {
            "objective": "Preserve verified work", "imp": 1, "constraints": [],
            "requirements": [
                {"id": "a", "text": "A stays good", "priority": 5,
                 "verify": {"kind": "file", "path": "a.txt", "contains": ["good"],
                            "level": "observed"}},
                {"id": "b", "text": "Tests pass", "priority": 4,
                 "verify": {"kind": "command",
                            "command": "python3 -m unittest discover -s verifier_tests -q",
                            "expect_exit": 0, "level": "observed"}},
            ],
        }
        model.start_goal(contract, self.root)
        first = evaluator.verify_requirement(self.root, "a")
        second = evaluator.verify_requirement(self.root, "b")

        self.assertTrue(first["passed"])
        self.assertFalse(second["passed"])
        self.assertIn("mutated workspace", second["summary"])
        self.assertEqual(model.load_state(self.root)["mutation_generation"], 1)
        self.assertEqual(evaluator.evaluate_goal(self.root)["verdict"], "not_met")

    def test_terminal_blocker_requires_structured_verified_evidence(self):
        model.start_goal(command_contract(), self.root)
        with self.assertRaisesRegex(ValueError, "evidence must be a verifier"):
            evaluator.record_terminal_blocker(
                self.root,
                {"reason": "I say impossible", "evidence": "I say external"},
            )

    def test_terminal_blocker_cannot_use_controller_state_as_evidence(self):
        model.start_goal(command_contract(), self.root)
        with self.assertRaisesRegex(ValueError, "controller state"):
            evaluator.record_terminal_blocker(self.root, {
                "reason": "I say impossible",
                "evidence": {"kind": "file", "path": ".dopa/goal.json",
                             "contains": ["Prove the work"]},
            })

    def test_regression_and_pending_outcome_precede_impossible(self):
        state = model.start_goal(command_contract(), self.root)
        state["known_regression"] = "broken"
        state["selected_action"] = {"id": "work", "awaiting_outcome": True}
        state["terminal_blocker"] = {
            "reason": "External blocker", "evidence": {"passed": True}
        }
        model.save_state(state, self.root)

        result = evaluator.evaluate(model.load_state(self.root))

        self.assertEqual(result["verdict"], "not_met")
        self.assertIn("regression", result["reason"])


if __name__ == "__main__":
    unittest.main()
