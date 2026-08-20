#!/usr/bin/env python3
"""Stop gate: refuse to end a turn when the last test run failed.

This is the whole enforcement surface. The v0.1 runtime had four gates and
every one of them checked whether a file had been read or a line had been
typed — paperwork the agent authors itself. In the 2026-08-19 sweep the
completion gate fired in all five treatment sessions and passed code failing
three of five visible tests, because reading `completion.md` satisfied it.

This gate reads something the agent cannot author: the output a test runner
produced. `is_error` is useless here — a shell that successfully runs a failing
suite exits 0 — so the verdict comes from the runner's own summary line.

Exit 2 blocks the stop and stderr becomes the reason. Fails open on any error.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

SKILL_NAME = "dopa-kernel"
MAX_BLOCKS = 2

_RUNNER = re.compile(
    r"\b(pytest|py\.test|npm\s+(run\s+)?test|yarn\s+test|jest|vitest|"
    r"cargo\s+test|go\s+test|mvn\s+test|rspec|phpunit|ctest)\b")

# Each runner's own summary of failure. Ordered most specific first.
_FAILED = (
    re.compile(r"\b(\d+)\s+failed\b"),              # pytest
    re.compile(r"\b(\d+)\s+failing\b"),             # mocha
    re.compile(r"^FAILED\b", re.M),                 # pytest node id lines
    re.compile(r"test result:\s*FAILED", re.I),     # cargo
    re.compile(r"^---\s*FAIL", re.M),               # go
    re.compile(r"Tests:.*?(\d+)\s+failed", re.S),   # jest
)
_PASSED = (
    re.compile(r"\b\d+\s+passed\b(?!.*\b\d+\s+failed\b)", re.S),
    re.compile(r"test result:\s*ok", re.I),
    re.compile(r"^ok\s", re.M),
)


def _text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(b.get("text", "") for b in content
                         if isinstance(b, dict) and isinstance(b.get("text"), str))
    return ""


def last_test_verdict(path: str) -> tuple[bool, str, str] | None:
    """(kernel_active, verdict, evidence) for the final test run, or None."""
    active = False
    pending: dict[str, str] = {}
    verdict = evidence = None
    blocks = 0
    try:
        lines = Path(path).read_text(errors="replace").splitlines()
    except OSError:
        return None
    for line in lines:
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except ValueError:
            continue
        if "gate: last test run failed" in line:
            blocks += 1
        message = record.get("message") or {}
        if not isinstance(message, dict):
            continue
        for block in message.get("content") or []:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "tool_use":
                inp = block.get("input") or {}
                if block.get("name") == "Skill" and inp.get("skill") == SKILL_NAME:
                    active = True
                cmd = str(inp.get("command") or "")
                if cmd and _RUNNER.search(cmd):
                    pending[str(block.get("id"))] = cmd
            elif block.get("type") == "tool_result":
                cmd = pending.pop(str(block.get("tool_use_id")), None)
                if cmd is None:
                    continue
                out = _text(block.get("content"))
                if any(p.search(out) for p in _FAILED):
                    verdict, evidence = "failed", _summary(out)
                elif any(p.search(out) for p in _PASSED):
                    verdict, evidence = "passed", ""
    if verdict is None or blocks >= MAX_BLOCKS:
        return None
    return active, verdict, evidence


def _summary(out: str) -> str:
    for pattern in _FAILED[:2]:
        match = pattern.search(out)
        if match:
            line = out[max(0, match.start() - 90):match.end() + 20].strip().splitlines()
            return line[-1] if line else match.group(0)
    return "the runner reported failures"


def main() -> int:
    try:
        payload = json.load(sys.stdin)
        result = last_test_verdict(payload.get("transcript_path") or "")
    except Exception:
        return 0
    if not result:
        return 0
    active, verdict, evidence = result
    if not active or verdict != "failed":
        return 0
    print(f"DopaKernel gate: last test run failed — {evidence}. You are not done. "
          f"Fix it and re-run, or state plainly in your reply that you are stopping "
          f"with tests failing and why.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
