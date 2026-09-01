#!/usr/bin/env python3
"""Validated, goal-scoped state for DopaKernel."""
from __future__ import annotations

import copy
import fcntl
import hashlib
import json
import os
import re
import shlex
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

STATE_DIR = ".dopa"
STATE_FILE = "goal.json"
SCHEMA_VERSION = 1
EVIDENCE_LEVELS = {"observed": 1, "independent": 2, "held-out": 3}
_SHELL_META = re.compile(r"[;&|<>\n\r]")


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def state_path(root: str | os.PathLike[str] | None = None) -> Path:
    return Path(root or os.getcwd()) / STATE_DIR / STATE_FILE


def lock_path(root: str | os.PathLike[str] | None = None) -> Path:
    return Path(root or os.getcwd()) / STATE_DIR / "goal.lock"


@contextmanager
def state_lock(root: str | os.PathLike[str] | None = None):
    path = lock_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+") as stream:
        fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def load_state(root: str | os.PathLike[str] | None = None) -> dict:
    try:
        value = json.loads(state_path(root).read_text())
    except FileNotFoundError:
        return {}
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid goal state: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError("invalid goal state: root must be an object")
    return value


def _integer(value: object, label: str, low: int = 1, high: int = 5) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        raise ValueError(f"{label} must be an integer from {low} to {high}")
    return value


def required_evidence_level(imp: int) -> str:
    if imp <= 2:
        return "observed"
    if imp == 3:
        return "independent"
    return "held-out"


def is_read_only_verifier(command: str) -> bool:
    if _SHELL_META.search(command):
        return False
    try:
        tokens = shlex.split(command)
    except ValueError:
        return False
    if not tokens:
        return False
    executable = Path(tokens[0]).name
    if executable in {"true", "false", "printf"}:
        return True
    if executable in {"pytest", "py.test", "jest", "vitest", "rspec", "phpunit", "ctest"}:
        return True
    if executable.startswith("python") and len(tokens) >= 3 and tokens[1] == "-m":
        return tokens[2] in {"unittest", "pytest"}
    if executable in {"cargo", "go"} and len(tokens) > 1:
        return tokens[1] == "test"
    if executable in {"npm", "yarn", "pnpm"} and len(tokens) > 1:
        return tokens[1] == "test" or tokens[1:3] == ["run", "test"]
    if executable in {"mvn", "mvnw", "gradle", "gradlew"}:
        return "test" in tokens[1:] and not any(
            item in tokens[1:] for item in ("deploy", "publish", "install")
        )
    if executable == "ruff" and len(tokens) > 1:
        return (tokens[1] == "check" and "--fix" not in tokens) or (
            tokens[1] == "format" and "--check" in tokens
        )
    if executable in {"mypy", "pyright", "shellcheck"}:
        return True
    if executable in {"tsc", "npx"}:
        return "--noEmit" in tokens or "--no-emit" in tokens
    if executable == "git" and len(tokens) > 1:
        return tokens[1] in {"status", "diff"} and not any(
            item.startswith("--output") for item in tokens[2:]
        )
    return False


def validate_contract(raw: dict) -> dict:
    if not isinstance(raw, dict):
        raise ValueError("goal contract must be a JSON object")
    objective = raw.get("objective")
    if not isinstance(objective, str) or not objective.strip():
        raise ValueError("objective must be a non-empty string")
    imp = _integer(raw.get("imp", 3), "imp")
    constraints = raw.get("constraints", [])
    if not isinstance(constraints, list) or not all(
        isinstance(item, str) and item.strip() for item in constraints
    ):
        raise ValueError("constraints must be a list of non-empty strings")
    requirements = raw.get("requirements")
    if not isinstance(requirements, list) or not requirements:
        raise ValueError("requirements must be a non-empty list")

    normalized_requirements = []
    ids: set[str] = set()
    for index, requirement in enumerate(requirements):
        if not isinstance(requirement, dict):
            raise ValueError(f"requirements[{index}] must be an object")
        rid = requirement.get("id")
        text = requirement.get("text")
        if not isinstance(rid, str) or not rid.strip():
            raise ValueError(f"requirements[{index}].id must be a non-empty string")
        if rid in ids:
            raise ValueError(f"duplicate requirement id: {rid}")
        ids.add(rid)
        if not isinstance(text, str) or not text.strip():
            raise ValueError(f"requirement {rid}.text must be a non-empty string")
        priority = _integer(requirement.get("priority", 3), f"requirement {rid}.priority")
        verify = requirement.get("verify")
        if not isinstance(verify, dict):
            raise ValueError(f"requirement {rid}.verify must be an object")
        kind = verify.get("kind")
        if kind not in ("command", "file"):
            raise ValueError(f"requirement {rid}.verify.kind must be command or file")
        level = verify.get("level", required_evidence_level(imp))
        if level not in EVIDENCE_LEVELS:
            raise ValueError(f"requirement {rid}.verify.level is invalid")
        minimum = required_evidence_level(imp)
        if EVIDENCE_LEVELS[level] < EVIDENCE_LEVELS[minimum]:
            raise ValueError(
                f"requirement {rid}.verify.level {level} is below imp {imp} floor {minimum}"
            )
        frozen_verify = {"kind": kind, "level": level}
        if kind == "command":
            command = verify.get("command")
            if not isinstance(command, str) or not command.strip():
                raise ValueError(f"requirement {rid}.verify.command must be non-empty")
            if not is_read_only_verifier(command):
                raise ValueError(
                    f"requirement {rid}.verify.command must be a recognized read-only verifier"
                )
            expect_exit = verify.get("expect_exit", 0)
            if isinstance(expect_exit, bool) or not isinstance(expect_exit, int):
                raise ValueError(f"requirement {rid}.verify.expect_exit must be an integer")
            frozen_verify.update(command=command, expect_exit=expect_exit)
            if "output_contains" in verify:
                marker = verify["output_contains"]
                if not isinstance(marker, str) or not marker:
                    raise ValueError(f"requirement {rid}.verify.output_contains must be non-empty")
                frozen_verify["output_contains"] = marker
        else:
            path = verify.get("path")
            if not isinstance(path, str) or not path.strip():
                raise ValueError(f"requirement {rid}.verify.path must be non-empty")
            contains = verify.get("contains", [])
            if not isinstance(contains, list) or not all(
                isinstance(marker, str) and marker for marker in contains
            ):
                raise ValueError(f"requirement {rid}.verify.contains must be a string list")
            frozen_verify.update(path=path, contains=list(contains))
        normalized_requirements.append(
            {"id": rid, "text": text, "priority": priority, "verify": frozen_verify}
        )

    return {
        "objective": objective.strip(),
        "imp": imp,
        "constraints": list(constraints),
        "requirements": normalized_requirements,
    }


def _goal_id(contract: dict) -> str:
    canonical = json.dumps(contract, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(canonical).hexdigest()[:16]


def save_state(state: dict, root: str | os.PathLike[str] | None = None) -> None:
    path = state_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = now()
    temporary_name = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", dir=path.parent, prefix="goal-", suffix=".tmp", delete=False
        ) as temporary:
            temporary_name = temporary.name
            temporary.write(json.dumps(state, indent=2, sort_keys=True) + "\n")
            temporary.flush()
            os.fsync(temporary.fileno())
        os.replace(temporary_name, path)
    finally:
        if temporary_name and Path(temporary_name).exists():
            Path(temporary_name).unlink()


def _start_goal(raw: dict, root: str | os.PathLike[str] | None = None) -> dict:
    existing = load_state(root)
    if existing and existing.get("status") not in ("complete", "impossible"):
        raise ValueError(
            f"unfinished goal {existing.get('goal_id', '?')} cannot be replaced; "
            "complete it before starting another"
        )
    contract = validate_contract(copy.deepcopy(raw))
    timestamp = now()
    state = {
        "schema_version": SCHEMA_VERSION,
        "goal_id": _goal_id(contract),
        "objective": contract["objective"],
        "imp": contract["imp"],
        "constraints": contract["constraints"],
        "requirements": [dict(requirement, evidence=None) for requirement in contract["requirements"]],
        "status": "active",
        "mutation_generation": 0,
        "selected_action": None,
        "candidates": [],
        "attempts": [],
        "closed_paths": [],
        "observations": [],
        "known_regression": None,
        "terminal_blocker": None,
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    save_state(state, root)
    return state


def start_goal(raw: dict, root: str | os.PathLike[str] | None = None) -> dict:
    with state_lock(root):
        return _start_goal(raw, root)


def record_mutation(
    root: str | os.PathLike[str] | None,
    source: str,
) -> dict:
    state = load_state(root)
    if not state:
        raise ValueError("no active goal")
    if state.get("status") != "active":
        raise ValueError(f"goal is {state.get('status')}, not active")
    state["mutation_generation"] = int(state.get("mutation_generation", 0)) + 1
    state["last_mutation"] = {"source": source, "at": now()}
    if state.get("selected_action"):
        state["selected_action"]["awaiting_outcome"] = True
    save_state(state, root)
    return state


def _record_terminal_blocker(raw: dict, root: str | os.PathLike[str] | None = None) -> dict:
    if not isinstance(raw, dict):
        raise ValueError("blocker must be a JSON object")
    reason = raw.get("reason")
    evidence = raw.get("evidence")
    if not isinstance(reason, str) or not reason.strip():
        raise ValueError("blocker.reason must be a non-empty string")
    if not isinstance(evidence, str) or not evidence.strip():
        raise ValueError("blocker.evidence must identify external evidence")
    state = load_state(root)
    if not state or state.get("status") != "active":
        raise ValueError("no active goal")
    state["terminal_blocker"] = {
        "reason": reason.strip(),
        "evidence": evidence.strip(),
        "recorded_at": now(),
    }
    save_state(state, root)
    return state


def record_terminal_blocker(raw: dict, root: str | os.PathLike[str] | None = None) -> dict:
    with state_lock(root):
        return _record_terminal_blocker(raw, root)
