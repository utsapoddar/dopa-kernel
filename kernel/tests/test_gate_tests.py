import json, os, subprocess, sys, tempfile, unittest
from pathlib import Path

GATE = str(Path(__file__).resolve().parents[1] / "gate_tests.py")


def trace(*records):
    fd, path = tempfile.mkstemp(suffix=".jsonl")
    with os.fdopen(fd, "w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")
    return path


def activate():
    return {"message": {"role": "assistant", "content": [
        {"type": "tool_use", "name": "Skill", "id": "s0", "input": {"skill": "dopa-kernel"}}]}}


def run(cmd, output, tid="t1", is_error=False):
    return (
        {"message": {"role": "assistant", "content": [
            {"type": "tool_use", "name": "Bash", "id": tid, "input": {"command": cmd}}]}},
        {"message": {"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": tid, "is_error": is_error,
             "content": output}]}},
    )


def gate(*records):
    path = trace(*records)
    try:
        p = subprocess.run([sys.executable, GATE], input=json.dumps({"transcript_path": path}),
                           capture_output=True, text=True)
        return p.returncode, p.stderr
    finally:
        os.remove(path)


class TestTestGate(unittest.TestCase):
    def test_failing_pytest_blocks(self):
        rc, err = gate(activate(), *run("pytest -q", "FF.\n3 failed, 2 passed in 0.02s"))
        self.assertEqual(rc, 2)
        self.assertIn("3 failed", err)

    def test_shell_exit_zero_does_not_mask_failure(self):
        # a shell that successfully runs a failing suite reports is_error False
        rc, _ = gate(activate(), *run("pytest -q", "1 failed, 4 passed", is_error=False))
        self.assertEqual(rc, 2)

    def test_passing_pytest_allows(self):
        rc, _ = gate(activate(), *run("pytest -q", "5 passed in 0.01s"))
        self.assertEqual(rc, 0)

    def test_last_run_wins_when_failure_is_fixed(self):
        rc, _ = gate(activate(),
                     *run("pytest -q", "2 failed, 3 passed", tid="a"),
                     *run("pytest -q", "5 passed in 0.01s", tid="b"))
        self.assertEqual(rc, 0)

    def test_regression_after_a_green_run_still_blocks(self):
        rc, _ = gate(activate(),
                     *run("pytest -q", "5 passed", tid="a"),
                     *run("pytest -q", "1 failed, 4 passed", tid="b"))
        self.assertEqual(rc, 2)

    def test_inert_when_kernel_not_active(self):
        rc, _ = gate(*run("pytest -q", "3 failed, 2 passed"))
        self.assertEqual(rc, 0)

    def test_no_test_run_is_not_a_failure(self):
        rc, _ = gate(activate(), *run("ls -la", "a.py b.py"))
        self.assertEqual(rc, 0)

    def test_other_runners_are_recognised(self):
        for cmd, out in (("cargo test", "test result: FAILED. 1 passed; 2 failed"),
                         ("go test ./...", "--- FAIL: TestThing\nFAIL"),
                         ("npm test", "Tests:  2 failed, 8 passed, 10 total")):
            with self.subTest(cmd=cmd):
                self.assertEqual(gate(activate(), *run(cmd, out))[0], 2)

    def test_blocking_stops_after_the_cap(self):
        prior = [{"message": {"role": "user", "content":
                  "DopaKernel gate: last test run failed — x"}, "isMeta": True}] * 2
        rc, _ = gate(activate(), *run("pytest -q", "3 failed, 2 passed"), *prior)
        self.assertEqual(rc, 0)

    def test_unreadable_transcript_fails_open(self):
        p = subprocess.run([sys.executable, GATE],
                           input=json.dumps({"transcript_path": "/nonexistent"}),
                           capture_output=True, text=True)
        self.assertEqual(p.returncode, 0)


if __name__ == "__main__":
    unittest.main()
