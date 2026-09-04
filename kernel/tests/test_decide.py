import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

K = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(K))
import gate_decide  # noqa: E402
import model  # noqa: E402
import policy  # noqa: E402


def goal():
    return {
        "objective": "Implement safely", "imp": 2, "constraints": [],
        "requirements": [{"id": "work", "text": "Work is verified", "priority": 5,
                          "verify": {"kind": "file", "path": "result.txt",
                                     "contains": ["done"], "level": "observed"}}],
    }


def candidate(cid="build", *, r="advanced"):
    return {
        "id": cid, "requirement_id": "work", "what": cid, "in_frame": True,
        "expected_r": r, "expected_i": "none", "cost": 1, "confidence": 5,
        "failure_recoverable": True, "uncertainty_reducible": False,
        "decision_critical_uncertainty": False, "restores_regression": False,
    }


class ShellClassificationTest(unittest.TestCase):
    def mutation(self, command):
        return gate_decide.is_mutation("Bash", {"command": command}, "/tmp/project")

    def test_exact_selector_command_is_control_not_mutation(self):
        command = f"{sys.executable} {K / 'decide.py'} status"
        self.assertTrue(gate_decide.is_control_command(command, "/tmp/project"))
        self.assertFalse(self.mutation(command))

    def test_compound_command_cannot_hide_behind_selector_exemption(self):
        command = f"{sys.executable} {K / 'decide.py'} status; touch owned"
        self.assertFalse(gate_decide.is_control_command(command, "/tmp/project"))
        self.assertTrue(self.mutation(command))

    def test_similarly_named_script_is_not_control(self):
        self.assertFalse(gate_decide.is_control_command("python3 /tmp/decide.py status", "/tmp"))

    def test_historical_shell_write_bypasses_are_mutations(self):
        commands = (
            "touch result.txt",
            "node -e \"require('fs').writeFileSync('result.txt','x')\"",
            "curl https://example.com/file -o result.txt",
            "cat /tmp/new > result.txt",
            "cp /tmp/candidates.json src/candidates.json",
            "python3 -c \"open('result.txt','w').write('x')\"",
        )
        for command in commands:
            with self.subTest(command=command):
                self.assertTrue(self.mutation(command))

    def test_known_reads_and_test_runs_are_not_mutations(self):
        for command in ("ls -la", "cat result.txt", "git diff", "python3 -m unittest -q"):
            with self.subTest(command=command):
                self.assertFalse(self.mutation(command))

    def test_unknown_shell_command_is_conservatively_a_mutation(self):
        self.assertTrue(self.mutation("custom-build-tool deploy"))

    def test_read_command_write_options_are_still_mutations(self):
        self.assertTrue(self.mutation("find . -name '*.tmp' -delete"))
        self.assertTrue(self.mutation("git diff --output=changes.patch"))

    def test_shell_substitution_is_never_read_only(self):
        self.assertTrue(self.mutation("ls $(touch owned)"))
        self.assertTrue(self.mutation("cat `touch owned`"))

    def test_only_actual_temporary_file_targets_are_exempt(self):
        self.assertFalse(gate_decide.is_mutation("Write", {"file_path": "/tmp/dopa-input.json"}, "/x"))
        self.assertTrue(gate_decide.is_mutation(
            "Write", {"file_path": "/project/src/candidates.json"}, "/project"))


class PreToolGateTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.trace = self.root / "trace.jsonl"
        self.trace.write_text(json.dumps({"message": {"role": "assistant", "content": [
            {"type": "tool_use", "name": "Skill", "input": {"skill": "dopa-kernel"}}
        ]}}) + "\n")

    def gate(self, command=None, *, active=True):
        payload = {
            "transcript_path": str(self.trace) if active else str(self.root / "missing"),
            "cwd": str(self.root),
            "tool_name": "Bash" if command else "Write",
            "tool_input": {"command": command} if command else {
                "file_path": str(self.root / "result.txt"), "content": "done"
            },
        }
        return subprocess.run([sys.executable, str(K / "gate_decide.py")],
                              input=json.dumps(payload), capture_output=True, text=True)

    def start_and_select(self):
        model.start_goal(goal(), self.root)
        policy.select_and_save([candidate()], self.root)

    def test_mutation_without_goal_is_blocked(self):
        result = self.gate()
        self.assertEqual(result.returncode, 2)
        self.assertIn("start", result.stderr)

    def test_mutation_without_selection_is_blocked(self):
        model.start_goal(goal(), self.root)
        result = self.gate()
        self.assertEqual(result.returncode, 2)
        self.assertIn("select", result.stderr)

    def test_valid_selection_allows_one_mutation_and_records_generation(self):
        self.start_and_select()
        result = self.gate()
        self.assertEqual(result.returncode, 0, result.stderr)
        state = model.load_state(self.root)
        self.assertEqual(state["mutation_generation"], 1)
        self.assertTrue(state["selected_action"]["awaiting_outcome"])

    def test_second_mutation_requires_observation_and_outcome(self):
        self.start_and_select()
        self.assertEqual(self.gate().returncode, 0)
        result = self.gate()
        self.assertEqual(result.returncode, 2)
        self.assertIn("outcome", result.stderr)

    def test_concurrent_mutations_cannot_both_pass_one_selection(self):
        self.start_and_select()
        payload = {
            "transcript_path": str(self.trace), "cwd": str(self.root),
            "tool_name": "Write",
            "tool_input": {"file_path": str(self.root / "result.txt"), "content": "done"},
        }
        processes = [
            subprocess.Popen([sys.executable, str(K / "gate_decide.py")],
                             stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, text=True)
            for _ in range(2)
        ]
        results = [process.communicate(json.dumps(payload)) for process in processes]
        self.assertEqual(sorted(process.returncode for process in processes), [0, 2], results)
        self.assertEqual(model.load_state(self.root)["mutation_generation"], 1)

    def test_tampered_selection_is_rejected(self):
        self.start_and_select()
        state = model.load_state(self.root)
        state["selected_action"]["id"] = "invented"
        model.save_state(state, self.root)
        result = self.gate()
        self.assertEqual(result.returncode, 2)
        self.assertIn("does not follow", result.stderr)

    def test_authoritative_state_cannot_be_written_by_tools(self):
        self.start_and_select()
        payload = {
            "transcript_path": str(self.trace),
            "cwd": str(self.root),
            "tool_name": "Write",
            "tool_input": {"file_path": str(self.root / ".dopa/goal.json"), "content": "{}"},
        }
        result = subprocess.run(
            [sys.executable, str(K / "gate_decide.py")],
            input=json.dumps(payload), capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("controller state is protected", result.stderr)

    def test_authoritative_state_cannot_be_read_by_tools(self):
        self.start_and_select()
        payload = {
            "transcript_path": str(self.trace),
            "cwd": str(self.root),
            "tool_name": "Read",
            "tool_input": {"file_path": str(self.root / ".dopa/goal.json")},
        }
        result = subprocess.run(
            [sys.executable, str(K / "gate_decide.py")],
            input=json.dumps(payload), capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("controller state is protected", result.stderr)

    def test_shell_cannot_target_authoritative_state(self):
        self.start_and_select()
        result = self.gate("cat .dopa/goal.json")
        self.assertEqual(result.returncode, 2)
        self.assertIn("controller state is protected", result.stderr)

    def test_documentation_may_mention_state_path(self):
        self.start_and_select()
        payload = {
            "transcript_path": str(self.trace),
            "cwd": str(self.root),
            "tool_name": "Write",
            "tool_input": {
                "file_path": str(self.root / "README.md"),
                "content": "Do not edit .dopa/goal.json directly.",
            },
        }
        result = subprocess.run(
            [sys.executable, str(K / "gate_decide.py")],
            input=json.dumps(payload), capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_unknown_tool_cannot_embed_a_controller_state_write(self):
        self.assertTrue(gate_decide.protected_state_access(
            "mcp__patch__apply",
            {"patch": "*** Update File: .dopa/goal.json"},
            str(self.root),
        ))

    def test_read_only_commands_do_not_need_a_goal(self):
        self.assertEqual(self.gate("git status").returncode, 0)

    def test_inert_when_not_activated(self):
        self.assertEqual(self.gate(active=False).returncode, 0)

    def test_active_goal_is_enforced_in_a_delegated_transcript(self):
        model.start_goal(goal(), self.root)
        result = self.gate(active=False)
        self.assertEqual(result.returncode, 2)
        self.assertIn("select", result.stderr)

    def test_terminal_goal_deactivates_even_if_transcript_invoked_skill(self):
        state = model.start_goal(goal(), self.root)
        for status in ("complete", "impossible", "cancelled"):
            with self.subTest(status=status):
                state["status"] = status
                model.save_state(state, self.root)
                self.assertFalse(gate_decide.kernel_active(str(self.trace), str(self.root)))

    def test_cancel_and_block_commands_require_native_user_approval(self):
        model.start_goal(goal(), self.root)
        for subcommand in ("cancel", "block"):
            with self.subTest(subcommand=subcommand):
                command = (
                    f"{sys.executable} {K / 'decide.py'} {subcommand} "
                    f"/tmp/dopa-{subcommand}.json"
                )
                result = self.gate(command)
                self.assertEqual(result.returncode, 0, result.stderr)
                decision = json.loads(result.stdout)["hookSpecificOutput"]
                self.assertEqual(decision["hookEventName"], "PreToolUse")
                self.assertEqual(decision["permissionDecision"], "ask")


if __name__ == "__main__":
    unittest.main()
