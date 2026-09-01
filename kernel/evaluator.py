#!/usr/bin/env python3
"""Structured verifiers and completion authority for DopaKernel."""
from __future__ import annotations

import hashlib
import json
import os
import shlex
import subprocess
from pathlib import Path

import model


def _digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _verifier_id(verify: dict) -> str:
    frozen = json.dumps(verify, sort_keys=True, separators=(",", ":")).encode()
    return _digest(frozen)[:16]


def _run_command(verify: dict, root: Path) -> tuple[bool, bytes, str]:
    before = _workspace_snapshot(root)
    completed = subprocess.run(
        shlex.split(verify["command"]),
        cwd=root,
        capture_output=True,
        timeout=300,
    )
    output = completed.stdout + completed.stderr
    passed = completed.returncode == verify.get("expect_exit", 0)
    marker = verify.get("output_contains")
    if marker is not None:
        passed = passed and marker.encode() in output
    summary = f"exit {completed.returncode}"
    if marker is not None and marker.encode() not in output:
        summary += f"; missing output marker {marker!r}"
    if _workspace_snapshot(root) != before:
        passed = False
        summary += "; verifier mutated workspace"
    return passed, output, summary


def _workspace_snapshot(root: Path) -> dict[str, str]:
    ignored_dirs = {".git", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
    ignored_files = {"goal.lock"}
    snapshot = {}
    for directory, dirnames, filenames in os.walk(root):
        dirnames[:] = [name for name in dirnames if name not in ignored_dirs]
        base = Path(directory)
        for name in filenames:
            path = base / name
            relative = path.relative_to(root)
            if name in ignored_files and relative.parts[:1] == (model.STATE_DIR,):
                continue
            try:
                if path.is_symlink():
                    value = f"link:{os.readlink(path)}".encode()
                else:
                    value = path.read_bytes()
            except OSError as exc:
                value = f"error:{exc}".encode()
            snapshot[str(relative)] = _digest(value)
    return snapshot


def _run_file(verify: dict, root: Path) -> tuple[bool, bytes, str]:
    path = Path(verify["path"])
    if not path.is_absolute():
        path = root / path
    try:
        content = path.read_bytes()
    except OSError as exc:
        return False, b"", f"cannot read {verify['path']}: {exc}"
    text = content.decode(errors="replace")
    missing = [marker for marker in verify.get("contains", []) if marker not in text]
    if missing:
        return False, content, f"missing required content: {missing}"
    return True, content, f"verified file {verify['path']}"


def _verify_requirement(root, requirement_id: str) -> dict:
    root_path = Path(root or ".").resolve()
    state = model.load_state(root_path)
    if not state:
        raise ValueError("no active goal")
    requirement = next(
        (item for item in state.get("requirements", []) if item.get("id") == requirement_id),
        None,
    )
    if requirement is None:
        raise ValueError(f"unknown requirement: {requirement_id}")
    verify = requirement["verify"]
    try:
        if verify["kind"] == "command":
            passed, output, summary = _run_command(verify, root_path)
        else:
            passed, output, summary = _run_file(verify, root_path)
    except subprocess.TimeoutExpired as exc:
        passed, output, summary = False, (exc.stdout or b"") + (exc.stderr or b""), "verifier timed out"
    except OSError as exc:
        passed, output, summary = False, b"", f"cannot execute verifier: {exc}"
    if "mutated workspace" in summary:
        state["mutation_generation"] = int(state.get("mutation_generation", 0)) + 1
        state["last_mutation"] = {"source": f"verifier:{requirement_id}", "at": model.now()}
        if state.get("selected_action"):
            state["selected_action"]["awaiting_outcome"] = True
    receipt = {
        "requirement_id": requirement_id,
        "verifier_id": _verifier_id(verify),
        "passed": passed,
        "level": verify["level"],
        "generation": state.get("mutation_generation", 0),
        "observed_at": model.now(),
        "output_digest": _digest(output),
        "summary": summary,
    }
    requirement["evidence"] = receipt
    state.setdefault("observations", []).append(receipt)
    model.save_state(state, root_path)
    return receipt


def verify_requirement(root, requirement_id: str) -> dict:
    with model.state_lock(root):
        return _verify_requirement(root, requirement_id)


def evaluate(state: dict) -> dict:
    if not state:
        return {"verdict": "not_met", "reason": "no goal contract exists", "requirement_id": None}
    if state.get("known_regression"):
        return {"verdict": "not_met", "reason": f"known regression: {state['known_regression']}",
                "requirement_id": None}
    if (state.get("selected_action") or {}).get("awaiting_outcome"):
        return {"verdict": "not_met", "reason": "selected mutation is missing an observed outcome",
                "requirement_id": None}
    if state.get("terminal_blocker"):
        blocker = state["terminal_blocker"]
        if not isinstance(blocker, dict) or not (blocker.get("receipt") or {}).get("passed"):
            return {"verdict": "not_met", "reason": "terminal blocker lacks verified evidence",
                    "requirement_id": None}
        return {"verdict": "impossible", "reason": blocker.get("reason"),
                "requirement_id": None}

    generation = state.get("mutation_generation", 0)
    minimum = model.required_evidence_level(int(state.get("imp", 3)))
    requirements = sorted(
        state.get("requirements", []), key=lambda item: (-item.get("priority", 3), item.get("id", ""))
    )
    for requirement in requirements:
        evidence = requirement.get("evidence")
        rid = requirement.get("id")
        if not evidence:
            return {"verdict": "not_met", "reason": f"missing evidence for {rid}",
                    "requirement_id": rid}
        if evidence.get("generation") != generation:
            return {"verdict": "not_met", "reason": f"stale evidence for {rid}; re-verify after mutation",
                    "requirement_id": rid}
        if not evidence.get("passed"):
            return {"verdict": "not_met", "reason": f"verifier failed for {rid}: {evidence.get('summary', '')}",
                    "requirement_id": rid}
        actual_level = evidence.get("level")
        if model.EVIDENCE_LEVELS.get(actual_level, 0) < model.EVIDENCE_LEVELS[minimum]:
            return {"verdict": "not_met",
                    "reason": f"evidence for {rid} is {actual_level}; imp {state.get('imp')} requires {minimum}",
                    "requirement_id": rid}
        expected_id = _verifier_id(requirement["verify"])
        if evidence.get("verifier_id") != expected_id:
            return {"verdict": "not_met", "reason": f"verifier identity changed for {rid}",
                    "requirement_id": rid}
    return {"verdict": "met", "reason": "all requirements have fresh passing evidence",
            "requirement_id": None}


def _evaluate_goal(root=None, *, finalize: bool = False) -> dict:
    state = model.load_state(root)
    result = evaluate(state)
    if finalize and result["verdict"] == "met":
        for requirement in state.get("requirements", []):
            if requirement.get("evidence"):
                _verify_requirement(root, requirement["id"])
        state = model.load_state(root)
        result = evaluate(state)
    elif finalize and result["verdict"] == "impossible":
        blocker = state["terminal_blocker"]
        passed, digest, summary = model.verify_blocker_evidence(blocker["evidence"], root)
        blocker["receipt"] = {"passed": passed, "digest": digest, "summary": summary}
        model.save_state(state, root)
        result = evaluate(state)
    terminal_status = {"met": "complete", "impossible": "impossible"}.get(result["verdict"])
    if finalize and terminal_status and state.get("status") != terminal_status:
        state["status"] = terminal_status
        state["completed_at"] = model.now()
        model.save_state(state, root)
    return result


def evaluate_goal(root=None, *, finalize: bool = False) -> dict:
    with model.state_lock(root):
        return _evaluate_goal(root, finalize=finalize)


def record_terminal_blocker(root, raw: dict) -> dict:
    return model.record_terminal_blocker(raw, root)
