#!/usr/bin/env python3
"""Path selection and abandonment, computed rather than asserted.

The agent infers the candidates and scores them -- that part is judgment and
cannot be mechanised. It does NOT choose. `select` applies a fixed lexicographic
rule to those inputs and returns the winner, and `gate_decide.py` recomputes the
same rule from the stored inputs before allowing work, so a record claiming a
choice the rule does not produce is rejected.

The rule, in order:

1. Irreversibility first. A candidate whose failure cannot be recovered is
   eligible only when no recoverable candidate exists. Spread never buys back
   an unrecoverable loss.
2. Reduce uncertainty when it is cheap AND it could change the answer. A
   low-confidence candidate whose uncertainty is reducible returns
   `reduce-first` instead of a path: go look, then select again. If the second
   selection picks the same path the first would have, the research was
   `i: none` and is reported as wasted.
3. Otherwise the CHEAPEST eligible path wins, not the safest. When failure is
   recoverable, a cheap failure is a cheap experiment and buys information the
   safe path never returns. Ties go to upside, then to confidence.

Abandonment is a count, not an argument: two consecutive worse-than-expected
outcomes on a path close it, and the next selection must exclude it.

    decide.py select   candidates.json   # compute and record the choice
    decide.py outcome  <better|as|worse> # record what actually happened
    decide.py status                     # current path, attempts, closures
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

STATE_DIR = ".dopa"
STATE_FILE = "decision.json"
SWITCH_AFTER = 2
FIELDS = ("id", "cost", "upside", "confidence", "failure_recoverable",
          "uncertainty_reducible")


def state_path(root: str | None = None) -> Path:
    return Path(root or os.getcwd()) / STATE_DIR / STATE_FILE


def load(root: str | None = None) -> dict:
    try:
        return json.loads(state_path(root).read_text())
    except (OSError, ValueError):
        return {}


def normalise(candidate: dict) -> dict:
    missing = [f for f in FIELDS if f not in candidate]
    if missing:
        raise ValueError(f"candidate {candidate.get('id', '?')} missing {missing}")
    out = {"id": str(candidate["id"]), "what": str(candidate.get("what", ""))}
    for f in ("cost", "upside", "confidence"):
        value = int(candidate[f])
        if not 1 <= value <= 5:
            raise ValueError(f"{candidate['id']}.{f} must be 1-5, got {value}")
        out[f] = value
    out["failure_recoverable"] = bool(candidate["failure_recoverable"])
    out["uncertainty_reducible"] = bool(candidate["uncertainty_reducible"])
    return out


def value_per_cost(candidate: dict) -> float:
    """Expected value per unit spent.

    This deliberately DOES combine upside with confidence -- they are the two
    halves of one quantity, and multiplying them is just expected value.
    It is not the forbidden collapse: `r` and `i` are different channels and are
    never traded against each other. Dividing by cost is what encodes "a cheap
    recoverable failure is a cheap experiment" without letting a cost-1 lottery
    ticket win on cheapness alone.
    """
    return candidate["upside"] * candidate["confidence"] / candidate["cost"]


def choose(candidates: list[dict], closed: list[str]) -> dict:
    """The rule. Pure: same inputs always give the same answer."""
    live = [c for c in candidates if c["id"] not in closed]
    if not live:
        return {"verdict": "exhausted", "path": None,
                "why": "every candidate has been closed by repeated failure; "
                       "re-enumerate or change the goal"}
    recoverable = [c for c in live if c["failure_recoverable"]]
    eligible = recoverable or live
    rule1 = ("only unrecoverable candidates remain" if not recoverable
             else "unrecoverable candidates excluded"
             if len(recoverable) < len(live) else "all candidates recoverable")

    unsure = [c for c in eligible if c["confidence"] <= 2 and c["uncertainty_reducible"]]
    if unsure:
        pick = max(unsure, key=lambda c: (c["upside"], -c["cost"]))
        return {"verdict": "reduce-first", "path": pick["id"], "why":
                f"{pick['id']} has confidence {pick['confidence']} and reducible "
                f"uncertainty: resolve it before committing, then select again",
                "rule": rule1}

    # A guess with confidence 1 is not a well-informed guess; drop it unless
    # nothing better exists.
    plausible = [c for c in eligible if c["confidence"] >= 2] or eligible
    pick = max(plausible, key=lambda c: (value_per_cost(c), c["confidence"], c["id"]))
    return {"verdict": "commit", "path": pick["id"], "why":
            f"best value per unit cost ({value_per_cost(pick):.2g}): upside "
            f"{pick['upside']} x confidence {pick['confidence']} / cost {pick['cost']}"
            f"{'; failure recoverable, so a cheap failure is a cheap experiment' if pick['failure_recoverable'] else ''}",
            "rule": rule1}


def cmd_select(path: str) -> int:
    raw = json.loads(Path(path).read_text())
    candidates = [normalise(c) for c in raw["candidates"]]
    if len({c["id"] for c in candidates}) != len(candidates):
        raise ValueError("candidate ids must be unique")
    prior = load()
    closed = prior.get("closed", [])
    result = choose(candidates, closed)
    history = prior.get("selections", [])
    wasted = None
    if history and history[-1].get("verdict") == "reduce-first":
        # the previous step said go and look; did looking change anything?
        before = choose(history[-1]["candidates"],
                        closed + [history[-1]["path"]])
        if result["verdict"] == "commit" and before.get("path") == result["path"]:
            wasted = (f"the research did not change the choice ({result['path']} "
                      f"either way): i=none, do not repeat that pattern")
    record = {
        "goal": raw.get("goal", ""),
        "candidates": candidates,
        "closed": closed,
        "verdict": result["verdict"],
        "path": result["path"],
        "why": result["why"],
        "attempts": [],
        "selections": history + [{"verdict": result["verdict"], "path": result["path"],
                                  "candidates": candidates}],
    }
    p = state_path(); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(record, indent=2) + "\n")
    print(f"{result['verdict']}: {result['path']} — {result['why']}")
    if wasted:
        print(f"note: {wasted}")
    return 0


def cmd_outcome(delta: str) -> int:
    if delta not in ("better", "as", "worse"):
        print("outcome must be better|as|worse", file=sys.stderr)
        return 64
    record = load()
    if not record.get("path"):
        print("no active selection; run `decide.py select` first", file=sys.stderr)
        return 65
    record.setdefault("attempts", []).append({"path": record["path"], "delta": delta})
    tail = [a for a in record["attempts"] if a["path"] == record["path"]][-SWITCH_AFTER:]
    closed_now = False
    if len(tail) == SWITCH_AFTER and all(a["delta"] == "worse" for a in tail):
        record.setdefault("closed", []).append(record["path"])
        record["path"] = None
        record["verdict"] = "closed"
        closed_now = True
    state_path().write_text(json.dumps(record, indent=2) + "\n")
    if closed_now:
        print(f"{SWITCH_AFTER} consecutive worse-than-expected: path closed. "
              f"Re-select excluding it; repairing it further is sunk cost.")
    else:
        print(f"recorded {delta}")
    return 0


def cmd_status() -> int:
    record = load()
    if not record:
        print("no decision recorded")
        return 0
    print(json.dumps({k: record.get(k) for k in
                      ("goal", "verdict", "path", "why", "closed", "attempts")}, indent=2))
    return 0


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__.strip().splitlines()[-4], file=sys.stderr)
        return 64
    try:
        if argv[0] == "select" and len(argv) == 2:
            return cmd_select(argv[1])
        if argv[0] == "outcome" and len(argv) == 2:
            return cmd_outcome(argv[1])
        if argv[0] == "status":
            return cmd_status()
    except (ValueError, KeyError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 64
    print("usage: decide.py select <file> | outcome <better|as|worse> | status",
          file=sys.stderr)
    return 64


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
