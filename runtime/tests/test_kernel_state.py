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
