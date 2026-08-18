#!/usr/bin/env python3
"""PreToolUse gate: block mutations that precede required kernel invocations.

Exit 2 blocks the tool call and stderr becomes the blocking reason.
Fails open: any error exits 0.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kernel_state  # noqa: E402

MUTATORS = set(kernel_state.MUTATORS)
SCRATCH_MARKERS = ("/tmp/", "/private/tmp/", "scratchpad/")


def is_scratch(path: str) -> bool:
    return any(marker in path for marker in SCRATCH_MARKERS)


def decide(state, tool_name: str, tool_input: dict) -> str | None:
    """Return a blocking reason, or None to allow."""
    if not state.active or tool_name not in MUTATORS:
        return None
    if state.domain_adapter() is None:
        return ("K2 not satisfied: no domain adapter invoked. Read exactly one of "
                "modules/{artifact,decision,execution,combined}.md before working.")
    target = str(tool_input.get("file_path") or "")
    if not is_scratch(target) and "rollback.md" not in state.modules_read:
        return ("K4 not satisfied: persistent state change without a prepared rollback. "
                "Read modules/rollback.md, capture prior state, then act.")
    if state.latest_envelope_class() == "outside" and "proposal.md" not in state.modules_read:
        return ("K3 not satisfied: work is declared outside the envelope. Read "
                "modules/proposal.md and propose before implementing.")
    return None


def main() -> int:
    try:
        payload = json.load(sys.stdin)
        state = kernel_state.parse(payload.get("transcript_path") or "")
        reason = decide(state, payload.get("tool_name") or "", payload.get("tool_input") or {})
    except Exception:
        return 0
    if reason:
        print(f"DopaKernel gate: {reason}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
