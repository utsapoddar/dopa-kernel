#!/usr/bin/env python3
"""PreToolUse gate: no work until the rule has chosen a path.

This does not check that the agent wrote something down. It recomputes
`decide.choose()` from the inputs stored in the record and compares the result
to the recorded choice. A hand-authored record claiming a path the rule does
not produce is rejected, so the agent can be wrong about a candidate's cost or
confidence -- that is inference -- but cannot be wrong about what follows from
the numbers it gave.

It also refuses work on a path the outcome counter has closed, which is what
makes abandonment mechanical rather than a matter of resolve.

Exit 2 blocks and stderr is the reason. Fails open on any error.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import decide  # noqa: E402

SELECTOR = Path(__file__).resolve().parent / "decide.py"

SKILL_NAME = "dopa-kernel"
MUTATORS = {"Write", "Edit", "NotebookEdit"}
DESTRUCTIVE = ("rm ", "rm -", "git push", "git reset --hard", "git clean",
               "drop table", "truncate", "shutdown", "mkfs", "dd if=")
# Writing through the shell is still writing. C02 in the 2026-08-20 run hit a
# permission denial on Edit, said "routing the same write through Bash", and in
# doing so walked past a gate that only looked at Write/Edit and destructive
# commands. Selection has to precede ALL work, not just dangerous work.
_WRITES = re.compile(
    r"(?<![0-9&])>{1,2}\s*(?!&)(?!/dev/null)(?!/dev/stderr)\S"   # redirects
    r"|\btee\b"
    r"|\bsed\b[^|]*-i"
    r"|\b(cp|mv|install)\b[^|]*\s\S+\s\S+"
    r"|\bpatch\b|\bapply_patch\b"
    r"|\bpython3?\s+-c\b[^|]*(open\(|write_text|Path\()")
# Split deliberately: a substring match against the whole command is far too
# generous -- "/tmp/" anywhere in a command would have excused a write to a real
# source file elsewhere in the same line.
EXEMPT_PATH = (decide.STATE_DIR, "candidates.json", "process-notes",
               "/tmp/", "/private/tmp/")
EXEMPT_CMD = (decide.STATE_DIR, "candidates.json", "process-notes", "decide.py")


def kernel_active(path: str) -> bool:
    try:
        lines = Path(path).read_text(errors="replace").splitlines()
    except OSError:
        return False
    for line in lines:
        if '"dopa-kernel"' not in line:
            continue
        try:
            record = json.loads(line)
        except ValueError:
            continue
        message = record.get("message") or {}
        if not isinstance(message, dict):
            continue
        for block in message.get("content") or []:
            if (isinstance(block, dict) and block.get("type") == "tool_use"
                    and block.get("name") == "Skill"
                    and (block.get("input") or {}).get("skill") == SKILL_NAME):
                return True
    return False


def is_work(tool: str, tool_input: dict) -> bool:
    """Does this call change the world, rather than look at it or record a decision?"""
    target = str(tool_input.get("file_path") or "")
    command = str(tool_input.get("command") or "")
    if target and any(marker in target for marker in EXEMPT_PATH):
        return False
    if command and any(marker in command for marker in EXEMPT_CMD):
        return False
    if tool in MUTATORS:
        return True
    if tool != "Bash":
        return False
    return any(d in command for d in DESTRUCTIVE) or bool(_WRITES.search(command))


def decision_fault(cwd: str | None) -> str | None:
    record = decide.load(cwd)
    if not record:
        return ("no path selected. Enumerate the candidate ways to reach the goal, "
                "score each on cost/upside/confidence (1-5), whether its failure is "
                "recoverable, and whether its uncertainty is cheaply reducible, then "
                f"run `python3 {SELECTOR} select <file>`. You do not pick; the rule does.")
    recomputed = decide.choose(record.get("candidates", []), record.get("closed", []))
    if (recomputed["verdict"] != record.get("verdict")
            or recomputed["path"] != record.get("path")):
        return (f"the recorded choice does not follow from the recorded inputs: the rule "
                f"gives {recomputed['verdict']}/{recomputed['path']}, the record claims "
                f"{record.get('verdict')}/{record.get('path')}. Re-run decide.py select.")
    if record.get("verdict") == "reduce-first":
        return (f"the rule returned reduce-first on {record['path']}: its uncertainty is "
                f"cheaply reducible and could change the answer. Go resolve it, then "
                f"select again. Do not start building yet.")
    if record.get("verdict") in ("closed", "exhausted"):
        return (f"path closed after repeated worse-than-expected outcomes. Re-select "
                f"excluding {record.get('closed')}; continuing to repair it is sunk cost.")
    return None


def main() -> int:
    try:
        payload = json.load(sys.stdin)
        if not is_work(payload.get("tool_name") or "", payload.get("tool_input") or {}):
            return 0
        if not kernel_active(payload.get("transcript_path") or ""):
            return 0
        fault = decision_fault(payload.get("cwd"))
    except Exception:
        return 0
    if fault:
        print(f"DopaKernel gate: {fault}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
