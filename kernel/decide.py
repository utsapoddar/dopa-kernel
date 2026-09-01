#!/usr/bin/env python3
"""DopaKernel goal, action, evidence, and completion CLI.

    decide.py start <goal.json>
    decide.py select <candidates.json>
    decide.py outcome <observation.json>
    decide.py verify <requirement-id>
    decide.py block <blocker.json>
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
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0 if receipt["passed"] else 1


def cmd_block(path: str) -> int:
    state = model.record_terminal_blocker(_read_json(path))
    print(f"terminal blocker recorded for {state['goal_id']}")
    return 0


def cmd_evaluate() -> int:
    result = evaluator.evaluate_goal(None, finalize=True)
    print(json.dumps(result, indent=2, sort_keys=True))
    return {"met": 0, "not_met": 1, "impossible": 3}[result["verdict"]]


def cmd_status() -> int:
    state = model.load_state()
    if not state:
        print(json.dumps({"status": "none"}, indent=2))
        return 0
    result = evaluator.evaluate(state)
    view = {
        key: state.get(key) for key in (
            "goal_id", "objective", "imp", "status", "mutation_generation",
            "selected_action", "closed_paths", "attempts", "requirements",
            "known_regression", "terminal_blocker",
        )
    }
    view["evaluation"] = result
    print(json.dumps(view, indent=2, sort_keys=True))
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
        "block <blocker.json> | evaluate | status",
        file=sys.stderr,
    )
    return 64


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
