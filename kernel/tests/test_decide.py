import json, os, subprocess, sys, tempfile, unittest
from pathlib import Path

K = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(K))
import decide  # noqa: E402
import gate_decide as decide_gate  # noqa: E402


def cand(cid, cost, upside, confidence, recoverable=True, reducible=False):
    return {"id": cid, "cost": cost, "upside": upside, "confidence": confidence,
            "failure_recoverable": recoverable, "uncertainty_reducible": reducible}


def norm(*cs):
    return [decide.normalise(c) for c in cs]


A = cand("A", 4, 3, 5)                      # traditional, safe, costly
B = cand("B", 1, 5, 2)                      # cheap, big upside, low confidence
C = cand("C", 3, 4, 2, reducible=True)      # hybrid, uncertainty reducible


class TestRule(unittest.TestCase):
    def test_reducible_uncertainty_defers_the_commit(self):
        r = decide.choose(norm(A, B, C), [])
        self.assertEqual((r["verdict"], r["path"]), ("reduce-first", "C"))

    def test_cheap_recoverable_experiment_beats_the_safe_path(self):
        r = decide.choose(norm(A, B), [])
        self.assertEqual(r["path"], "B")

    def test_near_certainty_beats_a_coin_flip_at_equal_cost(self):
        r = decide.choose(norm(B, cand("C", 1, 4, 5)), [])
        self.assertEqual(r["path"], "C")

    def test_unrecoverable_failure_is_excluded_while_alternatives_exist(self):
        r = decide.choose(norm(cand("X", 1, 5, 5, recoverable=False), A), [])
        self.assertEqual(r["path"], "A")

    def test_unrecoverable_is_allowed_only_when_it_is_all_there_is(self):
        r = decide.choose(norm(cand("X", 2, 4, 4, recoverable=False)), [])
        self.assertEqual(r["path"], "X")

    def test_a_lottery_ticket_does_not_win_on_cheapness(self):
        r = decide.choose(norm(cand("L", 1, 5, 1), cand("M", 2, 4, 4)), [])
        self.assertEqual(r["path"], "M")

    def test_closed_paths_are_never_chosen(self):
        r = decide.choose(norm(A, B), ["B"])
        self.assertEqual(r["path"], "A")

    def test_closing_every_path_is_reported_not_guessed(self):
        r = decide.choose(norm(A, B), ["A", "B"])
        self.assertEqual(r["verdict"], "exhausted")
        self.assertIsNone(r["path"])

    def test_the_rule_is_pure(self):
        self.assertEqual(decide.choose(norm(A, B, C), []),
                         decide.choose(norm(A, B, C), []))

    def test_scores_outside_one_to_five_are_rejected(self):
        with self.assertRaises(ValueError):
            decide.normalise(cand("A", 9, 3, 3))

    def test_missing_fields_are_rejected(self):
        with self.assertRaises(ValueError):
            decide.normalise({"id": "A", "cost": 1})


class TestLifecycle(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.cwd = os.getcwd()
        os.chdir(self.dir)

    def tearDown(self):
        os.chdir(self.cwd)

    def run_cli(self, *args):
        p = subprocess.run([sys.executable, str(K / "decide.py"), *args],
                           capture_output=True, text=True, cwd=self.dir)
        return p.returncode, p.stdout + p.stderr

    def write(self, name, *cs):
        Path(self.dir, name).write_text(json.dumps({"goal": "X", "candidates": list(cs)}))
        return name

    def test_two_consecutive_worse_outcomes_close_the_path(self):
        self.run_cli("select", self.write("c.json", A, B))
        self.assertEqual(json.loads(Path(self.dir, ".dopa/decision.json").read_text())["path"], "B")
        self.run_cli("outcome", "worse")
        rc, out = self.run_cli("outcome", "worse")
        self.assertIn("path closed", out)
        record = json.loads(Path(self.dir, ".dopa/decision.json").read_text())
        self.assertEqual(record["closed"], ["B"])
        self.assertIsNone(record["path"])

    def test_a_good_outcome_between_failures_does_not_close_the_path(self):
        self.run_cli("select", self.write("c.json", A, B))
        for delta in ("worse", "as", "worse"):
            self.run_cli("outcome", delta)
        record = json.loads(Path(self.dir, ".dopa/decision.json").read_text())
        self.assertEqual(record["closed"], [])
        self.assertEqual(record["path"], "B")

    def test_reselect_after_closure_picks_a_different_path(self):
        self.run_cli("select", self.write("c.json", A, B))
        self.run_cli("outcome", "worse"); self.run_cli("outcome", "worse")
        rc, out = self.run_cli("select", "c.json")
        self.assertIn("A", out)

    def test_research_that_changes_nothing_is_reported_as_wasted(self):
        self.run_cli("select", self.write("c1.json", A, B, C))          # reduce-first C
        rc, out = self.run_cli("select", self.write("c2.json", A, B, cand("C", 3, 4, 4)))
        self.assertIn("did not change the choice", out)

    def test_research_that_changes_the_choice_is_not_flagged(self):
        self.run_cli("select", self.write("c1.json", A, B, C))
        rc, out = self.run_cli("select", self.write("c2.json", A, B, cand("C", 1, 5, 5)))
        self.assertNotIn("did not change", out)

    def test_outcome_without_a_selection_is_refused(self):
        rc, out = self.run_cli("outcome", "worse")
        self.assertEqual(rc, 65)

    def test_bad_outcome_word_is_refused(self):
        self.run_cli("select", self.write("c.json", A, B))
        self.assertEqual(self.run_cli("outcome", "great")[0], 64)


class TestGate(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.trace = Path(self.dir, "t.jsonl")
        self.trace.write_text(json.dumps({"message": {"role": "assistant", "content": [
            {"type": "tool_use", "name": "Skill", "input": {"skill": "dopa-kernel"}}]}}) + "\n")

    def gate(self, tool="Write", tool_input=None, active=True):
        trace = str(self.trace) if active else "/nonexistent"
        payload = {"transcript_path": trace, "cwd": self.dir, "tool_name": tool,
                   "tool_input": tool_input or {"file_path": f"{self.dir}/app.py", "content": "x"}}
        p = subprocess.run([sys.executable, str(K / "gate_decide.py")],
                           input=json.dumps(payload), capture_output=True, text=True)
        return p.returncode, p.stderr

    def select(self, *cs):
        Path(self.dir, "c.json").write_text(json.dumps({"goal": "X", "candidates": list(cs)}))
        subprocess.run([sys.executable, str(K / "decide.py"), "select", "c.json"],
                       cwd=self.dir, capture_output=True)

    def test_work_without_a_selection_is_blocked(self):
        rc, err = self.gate()
        self.assertEqual(rc, 2)
        self.assertIn("no path selected", err)

    def test_work_after_a_valid_commit_is_allowed(self):
        self.select(A, B)
        self.assertEqual(self.gate()[0], 0)

    def test_a_tampered_record_is_rejected(self):
        self.select(A, B)
        p = Path(self.dir, ".dopa/decision.json")
        record = json.loads(p.read_text()); record["path"] = "A"
        p.write_text(json.dumps(record))
        rc, err = self.gate()
        self.assertEqual(rc, 2)
        self.assertIn("does not follow from the recorded inputs", err)

    def test_building_during_reduce_first_is_blocked(self):
        self.select(A, B, C)
        rc, err = self.gate()
        self.assertEqual(rc, 2)
        self.assertIn("reduce-first", err)

    def test_recording_the_decision_is_never_blocked(self):
        for target in (f"{self.dir}/candidates.json", f"{self.dir}/.dopa/x.json"):
            self.assertEqual(self.gate(tool_input={"file_path": target, "content": "{}"})[0], 0)

    def test_running_the_selector_is_never_blocked(self):
        self.assertEqual(self.gate(tool="Bash",
                                   tool_input={"command": "python3 kernel/decide.py select c.json"})[0], 0)

    def test_reading_is_never_blocked(self):
        self.assertEqual(self.gate(tool="Read", tool_input={"file_path": "/etc/hosts"})[0], 0)

    def test_recoverable_shell_is_not_gated(self):
        self.assertEqual(self.gate(tool="Bash", tool_input={"command": "ls -la"})[0], 0)

    def test_destructive_shell_is_gated(self):
        rc, _ = self.gate(tool="Bash", tool_input={"command": "rm -rf build"})
        self.assertEqual(rc, 2)

    def test_inert_when_the_kernel_is_not_active(self):
        self.assertEqual(self.gate(active=False)[0], 0)


if __name__ == "__main__":
    unittest.main()


class TestShellWritesAreWork(unittest.TestCase):
    """C02 routed a write through Bash after a permission denial and thereby
    skipped selection entirely. Shell writes must be gated like any other."""

    def work(self, command):
        return decide_gate.is_work("Bash", {"command": command})

    def test_redirects_are_work(self):
        for c in ("cat > app.py <<'EOF'\nx\nEOF", "echo x >> app.py",
                  "printf 'x' > src/main.py"):
            self.assertTrue(self.work(c), c)

    def test_in_place_editors_are_work(self):
        for c in ("sed -i '' 's/a/b/' app.py", "tee app.py < /tmp/x",
                  "cp /tmp/new.py app.py", "python3 -c \"open('a.py','w').write('x')\""):
            self.assertTrue(self.work(c), c)

    def test_mentioning_tmp_does_not_excuse_writing_a_real_file(self):
        self.assertTrue(self.work("cp /tmp/patched.py src/main.py"))
        self.assertTrue(self.work("tee src/main.py < /tmp/x"))

    def test_reads_and_pipes_are_not_work(self):
        for c in ("cat app.py", "grep -n x app.py", "ls -la",
                  "pytest -q 2>&1 | tail -5", "shasum -a 256 app.py",
                  "python3 -m pytest -q > /dev/null"):
            self.assertFalse(self.work(c), c)

    def test_writing_the_decision_record_is_still_exempt(self):
        for c in ("cat > .dopa/candidates.json <<'EOF'\n{}\nEOF",
                  "cat > candidates.json <<'EOF'\n{}\nEOF",
                  "cat > process-notes.md <<'EOF'\nx\nEOF"):
            self.assertFalse(self.work(c), c)
