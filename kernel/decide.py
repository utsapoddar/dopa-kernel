#!/usr/bin/env python3
"""DopaKernel goal, action, evidence, and completion CLI.

    decide.py start <goal.json>
    decide.py select <candidates.json>
    decide.py outcome <observation.json>
    decide.py verify <requirement-id>
    decide.py block <blocker.json>
    decide.py cancel <cancel.json>
    decide.py evaluate
    decide.py status
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import evaluator
import model
import policy


def _read_json(path: str):
    return json.loads(Path(path).read_text())


def _emit(payload) -> None:
    """Print machine-readable output without pretty-print padding.

    Indentation costs context on every command an agent runs and carries no
    information the reader does not already get from the structure.
    """
    print(json.dumps(payload, sort_keys=True, separators=(",", ":")))


def cmd_start(path: str) -> int:
    state = model.start_goal(_read_json(path))
    print(f"started: {state['goal_id']} — {state['objective']}")
    return 0


def cmd_select(path: str) -> int:
    raw = _read_json(path)
    candidates = raw.get("candidates") if isinstance(raw, dict) else raw
    if not isinstance(candidates, list):
        raise ValueError("candidate file must be a list or contain a candidates list")
    result = policy.select_and_save(candidates)
    print(f"{result['verdict']}: {result['path']} — {result['why']}")
    return 0 if result["path"] else 1


def cmd_outcome(path: str) -> int:
    observation = _read_json(path)
    state = policy.record_outcome(None, observation)
    if not state.get("selected_action") and state.get("closed_paths"):
        print("outcome recorded; path closed; re-select")
    else:
        print(f"recorded r={observation['r']} i={observation['i']} δ={observation['delta']}")
    return 0


def cmd_verify(requirement_id: str) -> int:
    receipt = evaluator.verify_requirement(None, requirement_id)
    _emit(receipt)
    return 0 if receipt["passed"] else 1


def cmd_block(path: str) -> int:
    state = evaluator.record_terminal_blocker(None, _read_json(path))
    print(f"terminal blocker recorded for {state['goal_id']}")
    return 0


def cmd_cancel(path: str) -> int:
    state = model.cancel_goal(_read_json(path))
    print(f"cancelled: {state['cancelled_goal_id']} — {state['cancel_reason']}")
    return 0


def cmd_evaluate() -> int:
    result = evaluator.evaluate_goal(None, finalize=True)
    _emit(result)
    return {"met": 0, "not_met": 1, "impossible": 3}[result["verdict"]]


def cmd_status() -> int:
    state = model.load_state()
    if not state:
        _emit({"status": "none"})
        return 0
    result = evaluator.evaluate(state)
    view = {
        key: state.get(key) for key in (
            "goal_id", "objective", "imp", "status", "mutation_generation",
            "selected_action", "closed_paths", "requirements",
            "known_regression", "terminal_blocker",
        )
    }
    # Path closure reads only the last SWITCH_AFTER attempts (policy.py), so
    # older entries inform no decision. They stay in .dopa/goal.json; showing
    # them again on every status call is the single largest cost in a session.
    attempts = state.get("attempts") or []
    view["attempts"] = attempts[-policy.SWITCH_AFTER:]
    view["attempts_recorded"] = len(attempts)
    view["evaluation"] = result
    _emit(view)
    return 0


def main(argv: list[str]) -> int:
    try:
        if len(argv) == 2 and argv[0] == "start":
            return cmd_start(argv[1])
        if len(argv) == 2 and argv[0] == "select":
            return cmd_select(argv[1])
        if len(argv) == 2 and argv[0] == "outcome":
            return cmd_outcome(argv[1])
        if len(argv) == 2 and argv[0] == "verify":
            return cmd_verify(argv[1])
        if len(argv) == 2 and argv[0] == "block":
            return cmd_block(argv[1])
        if len(argv) == 2 and argv[0] == "cancel":
            return cmd_cancel(argv[1])
        if len(argv) == 1 and argv[0] == "evaluate":
            return cmd_evaluate()
        if len(argv) == 1 and argv[0] == "status":
            return cmd_status()
    except (ValueError, KeyError, OSError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 64
    print(
        "usage: decide.py start <goal.json> | select <candidates.json> | "
        "outcome <observation.json> | verify <requirement-id> | "
        "block <blocker.json> | cancel <cancel.json> | evaluate | status",
        file=sys.stderr,
    )
    return 64


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
