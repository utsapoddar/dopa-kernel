import sys, unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import compliance
from kernel_state import KernelState


def state(**kw):
    st = KernelState(active=kw.pop("active", True))
    st.modules_read = kw.pop("modules_read", {})
    # keep the derived view coherent with modules_read
    st.all_module_reads = {n: [i] for n, i in st.modules_read.items()}
    st.cells = kw.pop("cells", [])
    st.mutations = kw.pop("mutations", [])
    st.last_user_at = kw.pop("last_user_at", 0)
    st.user_turns = kw.pop("user_turns", [st.last_user_at])
    st.bash_ops = kw.pop("bash_ops", [])
    st.substantive_ops = kw.pop("substantive_ops", [st.last_user_at + 1])
    return st


REAL = "/Users/x/projects/app/main.py"
SCRATCH = "/private/tmp/z/scratchpad/n.md"


class TestAssess(unittest.TestCase):
    def test_inactive_session_yields_no_opportunities(self):
        r = compliance.assess(state(active=False))
        self.assertEqual(r, {})

    def test_adapter_opportunity_is_unconditional_for_active_sessions(self):
        r = compliance.assess(state(modules_read={}))
        self.assertTrue(r["adapter"]["opportunity"])
        self.assertFalse(r["adapter"]["compliant"])

    def test_adapter_compliant_when_read(self):
        r = compliance.assess(state(modules_read={"combined.md": 2}))
        self.assertTrue(r["adapter"]["compliant"])

    def test_adapter_noncompliant_when_read_after_first_mutation(self):
        st = state(modules_read={"combined.md": 9}, mutations=[(4, "Write", REAL)])
        self.assertFalse(compliance.assess(st)["adapter"]["compliant"])

    def test_rollback_has_no_opportunity_without_real_mutations(self):
        st = state(modules_read={"combined.md": 1}, mutations=[(3, "Write", SCRATCH)])
        self.assertFalse(compliance.assess(st)["rollback"]["opportunity"])

    def test_rollback_opportunity_on_real_mutation(self):
        st = state(modules_read={"combined.md": 1}, mutations=[(5, "Write", REAL)])
        r = compliance.assess(st)
        self.assertTrue(r["rollback"]["opportunity"])
        self.assertFalse(r["rollback"]["compliant"])

    def test_rollback_compliant_when_read_before_mutation(self):
        st = state(modules_read={"combined.md": 1, "rollback.md": 3},
                   mutations=[(5, "Write", REAL)])
        self.assertTrue(compliance.assess(st)["rollback"]["compliant"])

    def test_rollback_noncompliant_when_read_after_mutation(self):
        st = state(modules_read={"combined.md": 1, "rollback.md": 8},
                   mutations=[(5, "Write", REAL)])
        self.assertFalse(compliance.assess(st)["rollback"]["compliant"])

    def test_destructive_bash_creates_a_rollback_opportunity(self):
        st = state(modules_read={"combined.md": 1}, bash_ops=[(6, "destructive")])
        r = compliance.assess(st)
        self.assertTrue(r["rollback"]["opportunity"])
        self.assertFalse(r["rollback"]["compliant"])

    def test_destructive_bash_with_prior_rollback_is_compliant(self):
        st = state(modules_read={"combined.md": 1, "rollback.md": 4},
                   bash_ops=[(6, "destructive")])
        self.assertTrue(compliance.assess(st)["rollback"]["compliant"])

    def test_writing_bash_alone_is_no_rollback_opportunity(self):
        st = state(modules_read={"combined.md": 1}, bash_ops=[(6, "writing")])
        self.assertFalse(compliance.assess(st)["rollback"]["opportunity"])

    def test_turns_without_work_are_not_completion_opportunities(self):
        st = state(modules_read={}, user_turns=[2, 10], substantive_ops=[11])
        r = compliance.assess(st)
        self.assertEqual(r["completion"]["turns"], 1)

    def test_proposal_has_no_opportunity_without_outside_declaration(self):
        st = state(modules_read={"combined.md": 1}, cells=[(2, "C", "inside")])
        self.assertFalse(compliance.assess(st)["proposal"]["opportunity"])

    def test_proposal_opportunity_on_outside_declaration(self):
        st = state(modules_read={"combined.md": 1}, cells=[(7, "C", "outside")])
        r = compliance.assess(st)
        self.assertTrue(r["proposal"]["opportunity"])
        self.assertFalse(r["proposal"]["compliant"])

    def test_proposal_compliant_when_read_after_declaration(self):
        st = state(modules_read={"combined.md": 1, "proposal.md": 9},
                   cells=[(7, "C", "outside")])
        self.assertTrue(compliance.assess(st)["proposal"]["compliant"])

    def test_completion_opportunity_is_unconditional(self):
        r = compliance.assess(state(modules_read={}, last_user_at=5))
        self.assertTrue(r["completion"]["opportunity"])
        self.assertFalse(r["completion"]["compliant"])

    def test_completion_counts_each_turn_separately(self):
        st = state(modules_read={"completion.md": 3}, user_turns=[2, 10],
                   substantive_ops=[4, 11])
        st.all_module_reads = {"completion.md": [3]}
        r = compliance.assess(st)
        self.assertEqual((r["completion"]["turns"], r["completion"]["gated"]), (2, 1))
        self.assertFalse(r["completion"]["compliant"])

    def test_completion_compliant_when_every_turn_gates(self):
        st = state(modules_read={"completion.md": 12}, user_turns=[2, 10],
                   substantive_ops=[4, 11])
        st.all_module_reads = {"completion.md": [3, 12]}
        self.assertTrue(compliance.assess(st)["completion"]["compliant"])

    def test_completion_compliant_when_read_after_last_user_turn(self):
        st = state(modules_read={"completion.md": 11}, last_user_at=5)
        self.assertTrue(compliance.assess(st)["completion"]["compliant"])

    def test_cell_emission_tracked(self):
        self.assertFalse(compliance.assess(state())["cell_emission"]["compliant"])
        st = state(cells=[(3, "C", "inside")])
        self.assertTrue(compliance.assess(st)["cell_emission"]["compliant"])


class TestAggregate(unittest.TestCase):
    def test_rates_count_only_opportunities(self):
        rows = [
            {"adapter": {"opportunity": True, "compliant": True}},
            {"adapter": {"opportunity": True, "compliant": False}},
            {"rollback": {"opportunity": False, "compliant": None}},
        ]
        agg = compliance.aggregate(rows)
        self.assertEqual(agg["adapter"], {"opportunities": 2, "compliant": 1, "rate": 0.5})
        self.assertEqual(agg["rollback"], {"opportunities": 0, "compliant": 0, "rate": None})

    def test_per_turn_gates_aggregate_by_turn_not_by_session(self):
        rows = [{"completion": {"opportunity": True, "turns": 30, "gated": 1,
                                "compliant": False}}]
        agg = compliance.aggregate(rows)
        self.assertEqual(agg["completion"]["opportunities"], 30)
        self.assertEqual(agg["completion"]["compliant"], 1)

    def test_empty_input(self):
        self.assertEqual(compliance.aggregate([]), {})


if __name__ == "__main__":
    unittest.main()
