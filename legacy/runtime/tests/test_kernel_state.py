import json, sys, tempfile, unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import kernel_state


def transcript(records):
    fd = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False)
    for r in records:
        fd.write(json.dumps(r) + "\n")
    fd.close()
    return fd.name


def asst(*blocks):
    return {"type": "assistant", "message": {"role": "assistant", "content": list(blocks)}}


def user(text):
    return {"type": "user", "message": {"role": "user", "content": text}}


def meta(text):
    """Hook feedback: injected as a user-role record but flagged isMeta."""
    return {"type": "user", "isMeta": True,
            "message": {"role": "user", "content": text}}


def tool_use(name, **inp):
    return {"type": "tool_use", "name": name, "input": inp}


def text_block(t):
    return {"type": "text", "text": t}


SKILL = "/Users/x/.claude/skills/dopa-kernel/modules/"


class TestKernelState(unittest.TestCase):
    def test_inactive_when_skill_never_invoked(self):
        p = transcript([user("hi"), asst(text_block("hello"))])
        self.assertFalse(kernel_state.parse(p).active)

    def test_skill_invocation_activates(self):
        p = transcript([asst(tool_use("Skill", skill="dopa-kernel"))])
        st = kernel_state.parse(p)
        self.assertTrue(st.active)
        self.assertEqual(st.activated_at, 0)

    def test_other_skill_does_not_activate(self):
        p = transcript([asst(tool_use("Skill", skill="research"))])
        self.assertFalse(kernel_state.parse(p).active)

    def test_module_read_is_recorded(self):
        p = transcript([
            asst(tool_use("Skill", skill="dopa-kernel")),
            asst(tool_use("Read", file_path=SKILL + "combined.md")),
        ])
        st = kernel_state.parse(p)
        self.assertIn("combined.md", st.modules_read)
        self.assertEqual(st.domain_adapter(), "combined.md")

    def test_no_adapter_when_only_rollback_read(self):
        p = transcript([
            asst(tool_use("Skill", skill="dopa-kernel")),
            asst(tool_use("Read", file_path=SKILL + "rollback.md")),
        ])
        self.assertIsNone(kernel_state.parse(p).domain_adapter())

    def test_module_read_via_bash_command_is_recorded(self):
        p = transcript([
            asst(tool_use("Skill", skill="dopa-kernel")),
            asst(tool_use("Bash", command="cat " + SKILL + "completion.md")),
        ])
        self.assertIn("completion.md", kernel_state.parse(p).modules_read)

    def test_last_read_index_wins(self):
        p = transcript([
            asst(tool_use("Skill", skill="dopa-kernel")),
            asst(tool_use("Read", file_path=SKILL + "completion.md")),
            user("next"),
            asst(tool_use("Read", file_path=SKILL + "completion.md")),
        ])
        st = kernel_state.parse(p)
        self.assertEqual(st.modules_read["completion.md"], 3)

    def test_cell_lines_are_parsed(self):
        p = transcript([asst(text_block(
            "cell[C]: inside\ncell[r]: advanced\ncell[i]: none\n"))])
        st = kernel_state.parse(p)
        self.assertEqual([(0, "C", "inside"), (0, "r", "advanced"), (0, "i", "none")], st.cells)
        self.assertEqual(st.latest_envelope_class(), "inside")

    def test_latest_envelope_class_uses_most_recent(self):
        p = transcript([
            asst(text_block("cell[C]: inside")),
            asst(text_block("cell[C]: outside")),
        ])
        self.assertEqual(kernel_state.parse(p).latest_envelope_class(), "outside")

    def test_expect_lines_are_parsed(self):
        p = transcript([asst(text_block("expect[r]: advance (tests pass)"))])
        st = kernel_state.parse(p)
        self.assertEqual(st.expects, [(0, "r", "advance (tests pass)")])

    def test_last_user_at_tracks_user_turns(self):
        p = transcript([user("one"), asst(text_block("a")), user("two")])
        self.assertEqual(kernel_state.parse(p).last_user_at, 2)

    def test_mutations_are_recorded_with_index_and_path(self):
        p = transcript([
            asst(tool_use("Skill", skill="dopa-kernel")),
            asst(tool_use("Write", file_path="/Users/x/app/main.py")),
        ])
        st = kernel_state.parse(p)
        self.assertEqual(st.mutations, [(1, "Write", "/Users/x/app/main.py")])

    def test_edit_and_notebookedit_count_as_mutations(self):
        p = transcript([
            asst(tool_use("Edit", file_path="/a.py")),
            asst(tool_use("NotebookEdit", file_path="/b.ipynb")),
        ])
        st = kernel_state.parse(p)
        self.assertEqual([m[1] for m in st.mutations], ["Edit", "NotebookEdit"])

    def test_read_is_not_a_mutation(self):
        p = transcript([asst(tool_use("Read", file_path="/a.py"))])
        self.assertEqual(kernel_state.parse(p).mutations, [])

    def test_first_mutation_at_reports_earliest_index(self):
        p = transcript([
            asst(tool_use("Write", file_path="/a.py")),
            asst(tool_use("Write", file_path="/b.py")),
        ])
        self.assertEqual(kernel_state.parse(p).first_mutation_at(), 0)

    def test_first_mutation_at_is_none_without_mutations(self):
        p = transcript([asst(text_block("hi"))])
        self.assertIsNone(kernel_state.parse(p).first_mutation_at())

    def test_skill_name_records_which_skill_activated(self):
        p = transcript([asst(tool_use("Skill", skill="dopa-kernel"))])
        self.assertEqual(kernel_state.parse(p).skill_name, "dopa-kernel")

    def test_kernel_bookkeeping_is_not_substantive_work(self):
        """Invoking the skill and reading its own modules is routing, not work."""
        p = transcript([
            asst(tool_use("Skill", skill="dopa-kernel")),
            asst(tool_use("Read", file_path=SKILL + "artifact.md")),
        ])
        self.assertEqual(kernel_state.parse(p).substantive_ops, [])

    def test_real_tool_use_is_substantive(self):
        p = transcript([
            asst(tool_use("Skill", skill="dopa-kernel")),
            asst(tool_use("Bash", command="gh api user")),
            asst(tool_use("Write", file_path="/a.py")),
        ])
        self.assertEqual(kernel_state.parse(p).substantive_ops, [1, 2])

    def test_substantive_since_reports_work_after_an_index(self):
        p = transcript([
            asst(tool_use("Bash", command="ls")),
            user("go"),
            asst(tool_use("Bash", command="ls -la")),
        ])
        st = kernel_state.parse(p)
        self.assertTrue(st.substantive_since(1))
        self.assertFalse(st.substantive_since(99))

    def test_bash_state_changes_are_recorded_with_their_effect(self):
        p = transcript([
            asst(tool_use("Bash", command="ls -la")),
            asst(tool_use("Bash", command="echo x > f.txt")),
            asst(tool_use("Bash", command="git push origin main")),
        ])
        st = kernel_state.parse(p)
        self.assertEqual(st.bash_ops, [(1, "writing"), (2, "destructive")])

    def test_first_destructive_bash_at(self):
        p = transcript([
            asst(tool_use("Bash", command="echo x > f")),
            asst(tool_use("Bash", command="rm -rf build")),
        ])
        self.assertEqual(kernel_state.parse(p).first_destructive_at(), 1)

    def test_first_destructive_at_is_none_when_absent(self):
        p = transcript([asst(tool_use("Bash", command="ls"))])
        self.assertIsNone(kernel_state.parse(p).first_destructive_at())

    def test_cells_written_to_the_process_channel_are_seen(self):
        """K6 sends process records to a notes file, not the reply. A placement
        written there must still count, or the gate is blind to correct behaviour."""
        p = transcript([
            asst(tool_use("Write", file_path="/tmp/x/scratchpad/process-notes.md",
                          content="## envelope\ncell[C]: outside\ncell[r]: neutral\n")),
        ])
        st = kernel_state.parse(p)
        self.assertEqual(st.latest_envelope_class(), "outside")

    def test_cells_in_an_edit_new_string_are_seen(self):
        p = transcript([
            asst(tool_use("Edit", file_path="/tmp/x/scratchpad/process-notes.md",
                          old_string="a", new_string="cell[C]: inside")),
        ])
        self.assertEqual(kernel_state.parse(p).latest_envelope_class(), "inside")

    def test_cells_written_via_bash_heredoc_are_seen(self):
        """Notes are commonly written with `cat > notes <<EOF`, putting the
        placement in the Bash command rather than a Write input."""
        cmd = "cat > notes.md <<'EOF'\n## envelope\ncell[C]: outside\ncell[r]: neutral\nEOF"
        p = transcript([asst(tool_use("Bash", command=cmd))])
        self.assertEqual(kernel_state.parse(p).latest_envelope_class(), "outside")

    def test_grepping_for_cell_is_not_a_placement(self):
        p = transcript([asst(tool_use("Bash", command="grep -n 'cell\\[' notes.md"))])
        self.assertEqual(kernel_state.parse(p).cells, [])

    def test_prose_mentioning_cell_brackets_is_not_a_placement(self):
        p = transcript([asst(text_block("The `cell[C]` / `cell[r]` placements are ceremony"))])
        self.assertEqual(kernel_state.parse(p).cells, [])

    def test_hook_feedback_is_not_counted_as_a_user_turn(self):
        p = transcript([
            user("real request"),
            meta("Stop hook feedback:\n[gate_stop.py]: K5 not satisfied"),
            asst(text_block("continuing")),
        ])
        st = kernel_state.parse(p)
        self.assertEqual(st.user_turns, [0])
        self.assertEqual(st.last_user_at, 0)

    def test_all_reads_of_a_module_are_retained(self):
        p = transcript([
            asst(tool_use("Read", file_path=SKILL + "completion.md")),
            user("next"),
            asst(tool_use("Read", file_path=SKILL + "completion.md")),
        ])
        st = kernel_state.parse(p)
        self.assertEqual(st.all_module_reads["completion.md"], [0, 2])
        self.assertEqual(st.modules_read["completion.md"], 2)

    def test_user_turns_are_all_recorded(self):
        p = transcript([user("a"), asst(text_block("x")), user("b")])
        self.assertEqual(kernel_state.parse(p).user_turns, [0, 2])

    def test_missing_file_returns_inactive_state(self):
        st = kernel_state.parse("/nonexistent/path.jsonl")
        self.assertFalse(st.active)
        self.assertEqual(st.records, 0)

    def test_malformed_lines_are_skipped(self):
        fd = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False)
        fd.write("{not json\n")
        fd.write(json.dumps(asst(tool_use("Skill", skill="dopa-kernel"))) + "\n")
        fd.close()
        self.assertTrue(kernel_state.parse(fd.name).active)


if __name__ == "__main__":
    unittest.main()


class TestStakesParsing(unittest.TestCase):
    def scan(self, text):
        st = kernel_state.KernelState()
        kernel_state._scan_text(st, 7, text)
        return st

    def test_declaration_is_parsed(self):
        st = self.scan("imp: 4\ndue: 2026-09-08\n")
        self.assertEqual(st.imps, [(7, 4)])
        self.assertEqual(st.dues, [(7, "2026-09-08")])
        self.assertEqual(st.importance(), 4)
        self.assertEqual(st.due(), "2026-09-08")

    def test_kernel_menu_lines_are_not_declarations(self):
        st = self.scan("    imp: 1 | 2 | 3 | 4 | 5\n    due: YYYY-MM-DD | none\n")
        self.assertEqual(st.imps, [])
        self.assertEqual(st.dues, [])

    def test_undeclared_importance_defaults_to_three_but_reports_undeclared(self):
        st = self.scan("no stakes here")
        self.assertEqual(st.importance(), kernel_state.DEFAULT_IMP)
        self.assertIsNone(st.importance_declared_at())

    def test_quoted_and_bulleted_lines_still_declare(self):
        st = self.scan("- imp: 5 (Canada PR, unextendable)\n> due: none\n")
        self.assertEqual(st.importance(), 5)
        self.assertEqual(st.due(), "none")

    def test_out_of_range_importance_is_ignored(self):
        self.assertEqual(self.scan("imp: 7\n").imps, [])
        self.assertEqual(self.scan("imp: 0\n").imps, [])

    def test_latest_declaration_wins_but_first_marks_when_declared(self):
        st = self.scan("imp: 2\n")
        kernel_state._scan_text(st, 40, "imp: 5\n")
        self.assertEqual(st.importance(), 5)
        self.assertEqual(st.importance_declared_at(), 7)


class TestMalformedRecords(unittest.TestCase):
    def parse_lines(self, lines):
        import tempfile, os
        fd, path = tempfile.mkstemp(suffix=".jsonl")
        with os.fdopen(fd, "w") as f:
            f.write("\n".join(lines) + "\n")
        try:
            return kernel_state.parse(path)
        finally:
            os.remove(path)

    def test_string_message_does_not_crash_the_parser(self):
        st = self.parse_lines([
            '{"type":"system","message":"compact boundary"}',
            '{"type":"assistant","message":{"role":"assistant","content":['
            '{"type":"tool_use","name":"Skill","input":{"skill":"dopa-kernel"}}]}}',
        ])
        self.assertTrue(st.active)

    def test_null_and_missing_message_are_skipped(self):
        st = self.parse_lines(['{"type":"result"}', '{"type":"system","message":null}'])
        self.assertFalse(st.active)
