"""Tonic pacing: average reward rate and optimal latency.

Niv, Daw, Joel & Dayan 2007, Psychopharmacology 191:507-520, Eq. 4:

    tau* = sqrt(C_v / Rbar)

Optimal latency depends solely on the vigor cost constant and the average
reward rate, identically for every action.
"""
from __future__ import annotations

import math

DEFAULT_C_V = 1.0


def average_reward_rate(advanced_events: int, elapsed_seconds: float) -> float:
    """Rbar: verified-progress events per unit time."""
    if elapsed_seconds <= 0:
        return 0.0
    return advanced_events / elapsed_seconds


def optimal_latency(r_bar: float, c_v: float = DEFAULT_C_V) -> float:
    """tau* = sqrt(C_v / Rbar). Infinite when no verified progress has occurred."""
    if c_v <= 0:
        raise ValueError("c_v must be positive")
    if r_bar <= 0:
        return math.inf
    return math.sqrt(c_v / r_bar)


# --- Stakes: two axes that are deliberately never combined -------------------
#
# `imp` sets a FLOOR on evidence; `due` sets PACE above that floor. A tracker
# may fuse them into one score because sorting a queue needs a single ordering
# (see the 60/40 rule in the second brain's maintenance.py). An executor must
# not: "hurry" and "be careful" prescribe opposite actions on the same step, so
# there is no combine() here and there should never be one.

URGENCY_BANDS = ((0, 100), (3, 95), (7, 85), (14, 70), (30, 50), (60, 30), (90, 15))
NO_DEADLINE_URGENCY = 0
BEYOND_BANDS_URGENCY = 5

#: What `r: advanced` demands at each importance level (reference/matrix.md 8c).
EVIDENCE_FLOOR = {
    1: "observed",
    2: "observed",
    3: "not-hand-fit",
    4: "independent-or-held-out",
    5: "independent-or-held-out",
}


def urgency(days_left: int | None) -> int:
    """Deadline pressure 0-100, using the same bands as the warm-memory tracker.

    None (no deadline) is 0, not low-urgency-by-default: an item with no date
    is unpaced, not slow.
    """
    if days_left is None:
        return NO_DEADLINE_URGENCY
    if days_left < 0:
        return 100
    for threshold, value in URGENCY_BANDS[1:]:
        if days_left <= threshold:
            return value
    return BEYOND_BANDS_URGENCY


def evidence_floor(imp: int) -> str:
    """The evidence bar `imp` floors. Unknown levels fall back to the strictest."""
    return EVIDENCE_FLOOR.get(imp, "independent-or-held-out")
