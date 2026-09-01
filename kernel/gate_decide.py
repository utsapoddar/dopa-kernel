#!/usr/bin/env python3
"""PreToolUse gate for semantic action selection and mutation accounting.

Known reads are allowed. Unknown shell commands are mutations. A production
mutation requires an active goal and a policy-derived commit, and the gate
records the mutation before allowing it. Once active, gate errors fail closed.
"""
from __future__ import annotations

import json
import re
import shlex
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import model  # noqa: E402
import policy  # noqa: E402

SELECTOR = Path(__file__).resolve().parent / "decide.py"
SKILL_NAME = "dopa-kernel"
READ_TOOLS = {"Read", "Grep", "Glob", "LS"}
MUTATORS = {"Write", "Edit", "NotebookEdit"}
CONTROL_ARITY = {"start": 1, "select": 1, "outcome": 1, "verify": 1,
                 "block": 1, "evaluate": 0, "status": 0}
SHELL_META = re.compile(r"[;&|<>\n\r]")
READ_COMMANDS = {
    "ls", "pwd", "cat", "head", "tail", "grep", "rg", "find", "stat", "wc",
    "diff", "shasum", "sha256sum", "file", "which", "type", "realpath",
}
TEST_COMMANDS = {"pytest", "py.test", "jest", "vitest", "rspec", "phpunit", "ctest"}


def kernel_active(path: str) -> bool:
    try:
        lines = Path(path).read_text(errors="replace").splitlines()
    except OSError:
        return False
    for line in lines:
        try:
            record = json.loads(line)
        except (ValueError, TypeError):
            continue
        message = record.get("message") or {}
        if not isinstance(message, dict):
            continue
        for block in message.get("content") or []:
            if (
                isinstance(block, dict)
                and block.get("type") == "tool_use"
                and block.get("name") == "Skill"
                and (block.get("input") or {}).get("skill") == SKILL_NAME
            ):
                return True
    return False


def _script_tokens(command: str) -> list[str] | None:
    if SHELL_META.search(command):
        return None
    try:
        tokens = shlex.split(command)
    except ValueError:
        return None
    if not tokens:
        return None
    if Path(tokens[0]).name.startswith("python"):
        return tokens[1:]
    return tokens


def is_control_command(command: str, cwd: str | None) -> bool:
    tokens = _script_tokens(command)
    if not tokens or len(tokens) < 2:
        return False
    script = Path(tokens[0])
    resolved = script.resolve() if script.is_absolute() else (Path(cwd or ".") / script).resolve()
    if resolved != SELECTOR.resolve():
        return False
    subcommand = tokens[1]
    arity = CONTROL_ARITY.get(subcommand)
    return arity is not None and len(tokens[2:]) == arity


def _temporary_target(path: str) -> bool:
    if not path:
        return False
    target = Path(path).resolve()
    if target.suffix != ".json" or not target.name.startswith("dopa-"):
        return False
    roots = {
        Path("/tmp").resolve(),
        Path("/private/tmp").resolve(),
        Path(tempfile.gettempdir()).resolve(),
    }
    return any(target == root or root in target.parents for root in roots)


def _known_read_command(command: str) -> bool:
    if SHELL_META.search(command):
        return False
    try:
        tokens = shlex.split(command)
    except ValueError:
        return False
    if not tokens:
        return True
    executable = Path(tokens[0]).name
    if executable == "find" and any(
        token in {"-delete", "-exec", "-execdir", "-ok", "-okdir", "-fprint", "-fls"}
        for token in tokens[1:]
    ):
        return False
    if executable in READ_COMMANDS:
        return True
    if executable == "git" and len(tokens) > 1:
        return (
            tokens[1] in {"status", "diff", "log", "show", "rev-parse", "ls-files"}
            and not any(token.startswith("--output") for token in tokens[2:])
        )
    if executable in TEST_COMMANDS:
        return True
    if executable.startswith("python") and len(tokens) >= 3 and tokens[1] == "-m":
        return tokens[2] in {"unittest", "pytest"}
    if executable == "cargo" and len(tokens) > 1:
        return tokens[1] == "test"
    if executable == "go" and len(tokens) > 1:
        return tokens[1] == "test"
    if executable in {"npm", "yarn", "pnpm"} and len(tokens) > 1:
        return tokens[1:] in (["test"], ["run", "test"])
    return False


def is_mutation(tool: str, tool_input: dict, cwd: str | None = None) -> bool:
    if tool in READ_TOOLS:
        return False
    if tool in MUTATORS:
        return not _temporary_target(str(tool_input.get("file_path") or ""))
    if tool != "Bash":
        return True
    command = str(tool_input.get("command") or "")
    if is_control_command(command, cwd):
        return False
    return not _known_read_command(command)


def decision_fault(cwd: str | None) -> str | None:
    state = model.load_state(cwd)
    if not state:
        return ("no active goal. Write the user-visible contract under /tmp, then run "
                f"`python3 {SELECTOR} start <goal.json>`.")
    if state.get("status") != "active":
        return f"goal is {state.get('status')}; start a new goal before mutating"
    selected = state.get("selected_action") or {}
    if not selected:
        return ("no action selected. Enumerate requirement-aligned candidates under /tmp "
                f"and run `python3 {SELECTOR} select <candidates.json>`.")
    if selected.get("awaiting_outcome"):
        return ("the last mutation has no observation/outcome. Verify or inspect it, then run "
                f"`python3 {SELECTOR} outcome /tmp/dopa-outcome.json` before another mutation.")
    recomputed = policy.choose(state.get("candidates", []), state)
    if (
        recomputed.get("verdict") != selected.get("verdict")
        or recomputed.get("path") != selected.get("id")
    ):
        return ("the recorded action does not follow from the recorded candidates; "
                f"policy gives {recomputed.get('verdict')}/{recomputed.get('path')} but state "
                f"claims {selected.get('verdict')}/{selected.get('id')}. Re-select.")
    if selected.get("verdict") == "reduce-first":
        return ("policy returned reduce-first: resolve the decision-critical uncertainty and "
                "re-select before production mutation")
    return None


def main() -> int:
    try:
        payload = json.load(sys.stdin)
        transcript = payload.get("transcript_path") or ""
        if not kernel_active(transcript):
            return 0
        tool = payload.get("tool_name") or ""
        tool_input = payload.get("tool_input") or {}
        cwd = payload.get("cwd")
        if not is_mutation(tool, tool_input, cwd):
            return 0
        with model.state_lock(cwd):
            fault = decision_fault(cwd)
            if fault:
                print(f"DopaKernel gate: {fault}", file=sys.stderr)
                return 2
            model.record_mutation(cwd, tool)
        return 0
    except Exception as exc:
        print(f"DopaKernel gate: controller error; mutation blocked: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
