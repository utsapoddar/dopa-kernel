#!/usr/bin/env python3
"""Stop gate backed by frozen verifiers and fresh structured receipts.

The historical filename remains for settings compatibility. This gate never
parses test-like prose from the transcript. The independent evaluator is the
only completion authority for an active DopaKernel goal.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import evaluator  # noqa: E402
import gate_decide  # noqa: E402
import model  # noqa: E402


def main() -> int:
    try:
        payload = json.load(sys.stdin)
        if not gate_decide.kernel_active(payload.get("transcript_path") or ""):
            return 0
        root = payload.get("cwd")
        state = model.load_state(root)
        result = evaluator.evaluate(state)
        if result["verdict"] == "met":
            evaluator.evaluate_goal(root, finalize=True)
            return 0
        if result["verdict"] == "impossible":
            evaluator.evaluate_goal(root, finalize=True)
            return 0
        selected = (state.get("selected_action") or {}).get("id") if state else None
        next_action = f" Next selected action: {selected}." if selected else ""
        print(
            f"DopaKernel gate: goal not met — {result['reason']}.{next_action} "
            "Continue, re-select, or establish a real terminal blocker; do not declare victory.",
            file=sys.stderr,
        )
        return 2
    except Exception as exc:
        print(f"DopaKernel gate: completion evaluation failed closed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
