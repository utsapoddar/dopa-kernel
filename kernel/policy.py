#!/usr/bin/env python3
"""Deterministic semantic action policy for DopaKernel.

Progress (r) and information (i) remain separate channels. Hard eligibility and
requirement priority are applied before either channel is compared.
"""
from __future__ import annotations

from typing import Iterable

import model

SWITCH_AFTER = 2
R_VALUES = {"advanced", "neutral", "regressed"}
I_VALUES = {"decision-changing", "decision-constraining", "none"}
BOOL_FIELDS = (
    "in_frame",
    "failure_recoverable",
    "uncertainty_reducible",
    "decision_critical_uncertainty",
    "restores_regression",
)


def _score(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 5:
        raise ValueError(f"{label} must be an integer from 1 to 5")
    return value


def _boolean(value: object, label: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{label} must be a JSON boolean")
    return value


def normalise_candidate(raw: dict, requirement_ids: set[str]) -> dict:
    if not isinstance(raw, dict):
        raise ValueError("candidate must be an object")
    cid = raw.get("id")
    rid = raw.get("requirement_id")
    if not isinstance(cid, str) or not cid.strip():
        raise ValueError("candidate id must be a non-empty string")
    if rid not in requirement_ids:
        raise ValueError(f"candidate {cid}.requirement_id is not in the goal")
    expected_r = raw.get("expected_r")
    expected_i = raw.get("expected_i")
    if expected_r not in R_VALUES:
        raise ValueError(f"candidate {cid}.expected_r is invalid")
    if expected_i not in I_VALUES:
        raise ValueError(f"candidate {cid}.expected_i is invalid")
    out = {
        "id": cid.strip(),
        "requirement_id": rid,
        "what": str(raw.get("what", "")).strip(),
        "expected_r": expected_r,
        "expected_i": expected_i,
        "cost": _score(raw.get("cost"), f"candidate {cid}.cost"),
        "confidence": _score(raw.get("confidence"), f"candidate {cid}.confidence"),
    }
    for field in BOOL_FIELDS:
        out[field] = _boolean(raw.get(field, False), f"candidate {cid}.{field}")
    return out


def normalise_candidates(raw: Iterable[dict], state: dict) -> list[dict]:
    requirement_ids = {r["id"] for r in state.get("requirements", [])}
    candidates = [normalise_candidate(candidate, requirement_ids) for candidate in raw]
    ids = [candidate["id"] for candidate in candidates]
    if len(set(ids)) != len(ids):
        raise ValueError("candidate ids must be unique")
    return candidates


def _requirement_satisfied(requirement: dict, generation: int, imp: int) -> bool:
    evidence = requirement.get("evidence") or {}
    minimum = model.required_evidence_level(imp)
    return bool(
        evidence.get("passed")
        and evidence.get("generation") == generation
        and model.EVIDENCE_LEVELS.get(evidence.get("level"), 0)
        >= model.EVIDENCE_LEVELS[minimum]
    )


def _progress_key(candidate: dict) -> tuple[float, int, int, str]:
    return (
        candidate["confidence"] / candidate["cost"],
        candidate["confidence"],
        -candidate["cost"],
        candidate["id"],
    )


def _information_key(candidate: dict) -> tuple[int, int, str]:
    return (candidate["confidence"], -candidate["cost"], candidate["id"])


def choose(raw_candidates: Iterable[dict], state: dict) -> dict:
    """Choose a requirement-aligned action without summing r and i."""
    candidates = normalise_candidates(raw_candidates, state)
    closed = set(state.get("closed_paths", []))
    generation = int(state.get("mutation_generation", 0))
    imp = int(state.get("imp", 3))
    unmet = [
        requirement
        for requirement in state.get("requirements", [])
        if not _requirement_satisfied(requirement, generation, imp)
    ]
    if not unmet:
        return {"verdict": "goal-satisfied", "path": None,
                "why": "every requirement already has fresh passing evidence"}

    eligible = [
        candidate for candidate in candidates
        if candidate["id"] not in closed
        and candidate["in_frame"]
        and candidate["expected_r"] != "regressed"
    ]
    if state.get("known_regression"):
        restoration = [candidate for candidate in eligible if candidate["restores_regression"]]
        if restoration:
            eligible = restoration
        else:
            return {"verdict": "exhausted", "path": None,
                    "why": "a known regression must be restored before other work"}

    if not eligible:
        return {"verdict": "exhausted", "path": None,
                "why": "no live in-frame, non-regressing candidate remains"}

    priorities = {requirement["id"]: requirement["priority"] for requirement in unmet}
    serving_unmet = [candidate for candidate in eligible if candidate["requirement_id"] in priorities]
    if not serving_unmet:
        return {"verdict": "exhausted", "path": None,
                "why": "no candidate serves an unmet requirement"}
    highest = max(priorities[candidate["requirement_id"]] for candidate in serving_unmet)
    focused = [
        candidate for candidate in serving_unmet
        if priorities[candidate["requirement_id"]] == highest
    ]

    recoverable = [candidate for candidate in focused if candidate["failure_recoverable"]]
    if recoverable:
        focused = recoverable

    progress = [candidate for candidate in focused if candidate["expected_r"] == "advanced"]
    information = [
        candidate for candidate in focused
        if candidate["expected_r"] == "neutral"
        and candidate["expected_i"] == "decision-changing"
        and candidate["uncertainty_reducible"]
        and candidate["decision_critical_uncertainty"]
    ]

    clear_progress = [candidate for candidate in progress if candidate["confidence"] >= 3]
    if clear_progress:
        selected = max(clear_progress, key=_progress_key)
        return {"verdict": "commit", "path": selected["id"],
                "why": "highest-priority unmet requirement has a credible progress action"}
    if information:
        selected = max(information, key=_information_key)
        return {"verdict": "reduce-first", "path": selected["id"],
                "why": "decision-critical uncertainty can change the action choice"}
    if progress:
        selected = max(progress, key=_progress_key)
        return {"verdict": "commit", "path": selected["id"],
                "why": "best available progress action for the highest-priority unmet requirement"}
    return {"verdict": "exhausted", "path": None,
            "why": "remaining candidates neither advance nor resolve decision-critical uncertainty"}


def _select_and_save(raw_candidates: Iterable[dict], root=None) -> dict:
    state = model.load_state(root)
    if not state or state.get("status") != "active":
        raise ValueError("no active goal")
    if (state.get("selected_action") or {}).get("awaiting_outcome"):
        raise ValueError("record the selected action outcome before reselecting")
    candidates = normalise_candidates(raw_candidates, state)
    result = choose(candidates, state)
    state["candidates"] = candidates
    state["selected_action"] = None if result["path"] is None else {
        "id": result["path"],
        "verdict": result["verdict"],
        "why": result["why"],
        "awaiting_outcome": False,
    }
    state.setdefault("selections", []).append({
        "path": result["path"], "verdict": result["verdict"], "generation": state["mutation_generation"]
    })
    model.save_state(state, root)
    return result


def select_and_save(raw_candidates: Iterable[dict], root=None) -> dict:
    with model.state_lock(root):
        return _select_and_save(raw_candidates, root)


def _record_outcome(root, observation: dict) -> dict:
    if not isinstance(observation, dict):
        raise ValueError("outcome must be a JSON object")
    delta = observation.get("delta")
    progress = observation.get("r")
    information = observation.get("i")
    note = observation.get("note", "")
    if delta not in ("better", "as", "worse"):
        raise ValueError("outcome.delta must be better|as|worse")
    if progress not in R_VALUES:
        raise ValueError("outcome.r must be advanced|neutral|regressed")
    if information not in I_VALUES:
        raise ValueError("outcome.i must be decision-changing|decision-constraining|none")
    if not isinstance(note, str):
        raise ValueError("outcome.note must be a string")
    state = model.load_state(root)
    selected = state.get("selected_action") or {}
    path = selected.get("id")
    if not path:
        raise ValueError("no active selection")
    candidate = next(
        (item for item in state.get("candidates", []) if item.get("id") == path), {}
    )
    state.setdefault("attempts", []).append({
        "path": path,
        "delta": delta,
        "r": progress,
        "i": information,
        "note": note,
        "generation": state.get("mutation_generation", 0),
        "at": model.now(),
    })
    tail = state["attempts"][-SWITCH_AFTER:]
    close = progress == "neutral" and information == "none"
    close = close or (len(tail) == SWITCH_AFTER and all(
        attempt["path"] == path and attempt["delta"] == "worse" for attempt in tail
    ))
    if close:
        if path not in state.setdefault("closed_paths", []):
            state["closed_paths"].append(path)
    if progress == "regressed":
        state["known_regression"] = note or f"{path} produced a regression"
    elif candidate.get("restores_regression") and progress == "advanced" and delta != "worse":
        state["known_regression"] = None
    state["selected_action"] = None
    model.save_state(state, root)
    return state


def record_outcome(root, observation: dict) -> dict:
    with model.state_lock(root):
        return _record_outcome(root, observation)
