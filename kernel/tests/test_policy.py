import sys
import tempfile
import unittest
from pathlib import Path

K = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(K))
import model  # noqa: E402
import policy  # noqa: E402


def contract():
    return {
        "objective": "Ship without premature victory",
        "imp": 3,
        "constraints": [],
        "requirements": [
            {"id": "critical", "text": "Critical behavior works", "priority": 5,
             "verify": {"kind": "file", "path": "critical.txt",
                        "contains": ["done"], "level": "independent"}},
            {"id": "polish", "text": "Documentation is clear", "priority": 2,
             "verify": {"kind": "file", "path": "README.md",
                        "contains": ["Dopa"], "level": "independent"}},
        ],
    }


def candidate(cid, requirement="critical", *, r="advanced", i="none", confidence=4,
              cost=2, in_frame=True, recoverable=True, reducible=False,
              critical_uncertainty=False, restores_regression=False):
    return {
        "id": cid,
        "requirement_id": requirement,
        "what": cid,
        "in_frame": in_frame,
        "expected_r": r,
        "expected_i": i,
        "confidence": confidence,
        "cost": cost,
        "failure_recoverable": recoverable,
        "uncertainty_reducible": reducible,
        "decision_critical_uncertainty": critical_uncertainty,
        "restores_regression": restores_regression,
    }


class PolicyTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.state = model.start_goal(contract(), self.root)

    def test_out_of_frame_candidate_is_never_selected(self):
        result = policy.choose([
            candidate("outside", confidence=5, cost=1, in_frame=False),
            candidate("inside", confidence=3, cost=3),
        ], self.state)
        self.assertEqual((result["verdict"], result["path"]), ("commit", "inside"))

    def test_regressing_action_is_excluded_even_when_cheap(self):
        result = policy.choose([
            candidate("break-it", r="regressed", confidence=5, cost=1),
            candidate("advance", confidence=3, cost=4),
        ], self.state)
        self.assertEqual(result["path"], "advance")

    def test_highest_priority_unmet_requirement_wins(self):
        result = policy.choose([
            candidate("polish", requirement="polish", confidence=5, cost=1),
            candidate("critical", requirement="critical", confidence=3, cost=4),
        ], self.state)
        self.assertEqual(result["path"], "critical")

    def test_clear_progress_dominates_irrelevant_research(self):
        result = policy.choose([
            candidate("build", confidence=4, cost=3),
            candidate("research", r="neutral", i="decision-changing", confidence=5,
                      cost=1, reducible=True, critical_uncertainty=True),
        ], self.state)
        self.assertEqual((result["verdict"], result["path"]), ("commit", "build"))

    def test_decision_changing_research_precedes_only_uncertain_progress(self):
        result = policy.choose([
            candidate("guess", confidence=2, cost=3),
            candidate("inspect", r="neutral", i="decision-changing", confidence=5,
                      cost=1, reducible=True, critical_uncertainty=True),
        ], self.state)
        self.assertEqual((result["verdict"], result["path"]), ("reduce-first", "inspect"))

    def test_noncritical_research_is_not_reduce_first(self):
        result = policy.choose([
            candidate("guess", confidence=2),
            candidate("read-more", r="neutral", i="decision-changing", confidence=5,
                      cost=1, reducible=True, critical_uncertainty=False),
        ], self.state)
        self.assertEqual((result["verdict"], result["path"]), ("commit", "guess"))

    def test_unrecoverable_path_is_excluded_while_recoverable_progress_exists(self):
        result = policy.choose([
            candidate("unsafe", confidence=5, cost=1, recoverable=False),
            candidate("safe", confidence=3, cost=4),
        ], self.state)
        self.assertEqual(result["path"], "safe")

    def test_boolean_strings_in_candidates_are_rejected(self):
        bad = candidate("bad")
        bad["in_frame"] = "false"
        with self.assertRaisesRegex(ValueError, "JSON boolean"):
            policy.choose([bad], self.state)

    def test_known_regression_requires_a_restoration_candidate(self):
        self.state["known_regression"] = "API broke"
        result = policy.choose([candidate("unrelated")], self.state)
        self.assertEqual(result["verdict"], "exhausted")
        self.assertIn("restore", result["why"])

    def test_reselection_does_not_reset_two_strike_history(self):
        candidates = [candidate("build")]
        policy.select_and_save(candidates, self.root)
        policy.record_outcome(self.root, {"delta": "worse", "r": "neutral", "i": "decision-constraining"})
        policy.select_and_save(candidates, self.root)
        state = policy.record_outcome(
            self.root, {"delta": "worse", "r": "neutral", "i": "decision-constraining"})
        self.assertEqual(state["closed_paths"], ["build"])
        self.assertIsNone(state["selected_action"])

    def test_intervening_as_expected_breaks_the_worse_streak(self):
        for delta in ("worse", "as", "worse"):
            policy.select_and_save([candidate("build")], self.root)
            state = policy.record_outcome(
                self.root, {"delta": delta, "r": "advanced", "i": "none"})
        self.assertEqual(state["closed_paths"], [])

    def test_outcome_persists_observed_channels_and_consumes_selection(self):
        policy.select_and_save([candidate("build")], self.root)
        state = policy.record_outcome(
            self.root,
            {"delta": "as", "r": "advanced", "i": "decision-constraining", "note": "tests moved"},
        )
        self.assertEqual(state["attempts"][-1]["r"], "advanced")
        self.assertEqual(state["attempts"][-1]["i"], "decision-constraining")
        self.assertIsNone(state["selected_action"])

    def test_neutral_no_information_closes_stalled_path(self):
        policy.select_and_save([candidate("build")], self.root)
        state = policy.record_outcome(
            self.root, {"delta": "as", "r": "neutral", "i": "none"})
        self.assertEqual(state["closed_paths"], ["build"])

    def test_regression_is_recorded_and_successful_restoration_clears_it(self):
        policy.select_and_save([candidate("build")], self.root)
        state = policy.record_outcome(
            self.root, {"delta": "worse", "r": "regressed", "i": "decision-changing",
                        "note": "public API broke"})
        self.assertIn("public API broke", state["known_regression"])
        restoration = candidate("restore", restores_regression=True)
        policy.select_and_save([restoration], self.root)
        state = policy.record_outcome(
            self.root, {"delta": "as", "r": "advanced", "i": "none"})
        self.assertIsNone(state["known_regression"])


if __name__ == "__main__":
    unittest.main()
