import json
import sys
import tempfile
import unittest
from pathlib import Path

K = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(K))
import model  # noqa: E402


def contract(objective="Ship the feature", *, imp=3):
    return {
        "objective": objective,
        "imp": imp,
        "constraints": ["Do not change the public API"],
        "requirements": [
            {
                "id": "tests",
                "text": "The focused tests pass",
                "priority": 5,
                "verify": {
                    "kind": "command",
                    "command": "python3 -m unittest -q",
                    "expect_exit": 0,
                    "level": "independent",
                },
            }
        ],
    }


class GoalStateTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())

    def test_unfinished_goal_cannot_be_replaced(self):
        first = model.start_goal(contract(), self.root)
        with self.assertRaisesRegex(ValueError, "unfinished goal"):
            model.start_goal(contract("A different objective"), self.root)
        self.assertEqual(model.load_state(self.root)["goal_id"], first["goal_id"])

    def test_completed_goal_can_be_replaced_without_carrying_history(self):
        first = model.start_goal(contract(), self.root)
        first["attempts"].append({"path": "old", "delta": "worse"})
        first["closed_paths"].append("old")
        first["status"] = "complete"
        model.save_state(first, self.root)

        second = model.start_goal(contract("A new objective"), self.root)

        self.assertNotEqual(second["goal_id"], first["goal_id"])
        self.assertEqual(second["attempts"], [])
        self.assertEqual(second["closed_paths"], [])

    def test_mutation_generation_invalidates_prior_receipt_without_deleting_it(self):
        state = model.start_goal(contract(), self.root)
        state["requirements"][0]["evidence"] = {
            "passed": True,
            "generation": 0,
            "level": "independent",
        }
        model.save_state(state, self.root)

        changed = model.record_mutation(self.root, "Edit")

        self.assertEqual(changed["mutation_generation"], 1)
        self.assertTrue(changed["requirements"][0]["evidence"]["passed"])
        self.assertEqual(changed["requirements"][0]["evidence"]["generation"], 0)

    def test_contract_is_frozen_inside_state(self):
        source = contract()
        state = model.start_goal(source, self.root)
        source["requirements"][0]["verify"]["command"] = "true"

        saved = json.loads(model.state_path(self.root).read_text())
        self.assertEqual(
            saved["requirements"][0]["verify"]["command"],
            state["requirements"][0]["verify"]["command"],
        )

    def test_state_lock_serializes_controller_transitions(self):
        with model.state_lock(self.root):
            self.assertTrue(model.lock_path(self.root).exists())

    def test_mutating_command_cannot_hide_inside_a_verifier(self):
        bad = contract()
        bad["requirements"][0]["verify"]["command"] = "touch shipped.txt"
        with self.assertRaisesRegex(ValueError, "read-only verifier"):
            model.start_goal(bad, self.root)


if __name__ == "__main__":
    unittest.main()
