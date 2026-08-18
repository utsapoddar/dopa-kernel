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
