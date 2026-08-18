#!/usr/bin/env python3
"""Stop gate: block turn-end that precedes the completion gate.

Exit 2 prevents the agent from stopping and forces it to continue.
Blocks at most MAX_STOP_BLOCKS times per turn, then allows the stop so a model
that cannot satisfy the gate never wedges the session.
Fails open: any error exits 0.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kernel_state  # noqa: E402

MAX_STOP_BLOCKS = 2
STATE_DIR = Path.home() / ".claude" / "dopa-kernel" / "state"

REASON = ("K5 not satisfied: the completion gate has not run this turn. Read "
          "modules/completion.md, walk every envelope item as `item -> evidence` "
          "in the process channel, and name the highest-value remaining "
          "improvement before the final response.")


def decide(state) -> str | None:
    """Return a blocking reason, or None to allow the stop.

    Only turns that did substantive work are gated. Gating a turn that merely
    invoked the skill or answered a question produces noise with nothing to
    verify, which is the fastest way to make the kernel not worth running.
    """
    if not state.active:
        return None
    if not state.substantive_since(state.last_user_at):
        return None
    read_at = state.modules_read.get("completion.md")
    if read_at is None or read_at < state.last_user_at:
        return REASON
    return None


def _counter(session_id: str, prompt_id: str) -> Path:
    safe = f"{session_id}-{prompt_id}".replace("/", "_")
    return STATE_DIR / f"{safe}.count"


def block_count(session_id: str, prompt_id: str) -> int:
    try:
        return int(_counter(session_id, prompt_id).read_text().strip())
    except Exception:
        return 0


def bump(session_id: str, prompt_id: str) -> int:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    total = block_count(session_id, prompt_id) + 1
    _counter(session_id, prompt_id).write_text(str(total))
    return total


def main() -> int:
    try:
        payload = json.load(sys.stdin)
        state = kernel_state.parse(payload.get("transcript_path") or "")
        reason = decide(state)
        if not reason:
            return 0
        session_id = str(payload.get("session_id") or "unknown")
        prompt_id = str(payload.get("prompt_id") or "unknown")
        if block_count(session_id, prompt_id) >= MAX_STOP_BLOCKS:
            print(json.dumps({"systemMessage":
                              "DopaKernel: completion gate still unmet after "
                              f"{MAX_STOP_BLOCKS} blocks; allowing the stop."}))
            return 0
        bump(session_id, prompt_id)
    except Exception:
        return 0
    print(f"DopaKernel gate: {reason}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
