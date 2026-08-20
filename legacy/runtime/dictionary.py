"""The 18-cell value frame from reference/matrix.md, as executable code.

The frame is a PARTIAL order. compare() returns "incomparable" where the frame
declares incomparability; it never invents a ranking to break a tie.
"""
from __future__ import annotations

ENVELOPE = ("inside", "outside")
R_VALUES = ("advanced", "neutral", "regressed")
I_VALUES = ("decision-changing", "decision-constraining", "none")

CELLS = tuple((c, r, i) for c in ENVELOPE for r in R_VALUES for i in I_VALUES)

_R_RANK = {"regressed": 0, "neutral": 1, "advanced": 2}
_I_RANK = {"none": 0, "decision-constraining": 1, "decision-changing": 2}


def is_legal(cell) -> bool:
    if not isinstance(cell, tuple) or len(cell) != 3:
        return False
    envelope, r, i = cell
    return envelope in ENVELOPE and r in R_VALUES and i in I_VALUES


def is_eligible(cell) -> bool:
    """Rule 1, lexicographic gate: outside C has no value at any position."""
    return is_legal(cell) and cell[0] == "inside"


def compare(a, b) -> str:
    """Rule 3, Pareto partial order. One of a>b, b>a, equal, incomparable."""
    if not is_legal(a) or not is_legal(b):
        raise ValueError(f"illegal cell: {a!r} vs {b!r}")
    if a[0] != b[0]:
        return "a>b" if a[0] == "inside" else "b>a"
    if not is_eligible(a):
        return "equal"
    ar, ai = _R_RANK[a[1]], _I_RANK[a[2]]
    br, bi = _R_RANK[b[1]], _I_RANK[b[2]]
    if ar == br and ai == bi:
        return "equal"
    if ar >= br and ai >= bi:
        return "a>b"
    if br >= ar and bi >= ai:
        return "b>a"
    return "incomparable"


def violates_regression_floor(candidate, alternative) -> bool:
    """Rule 5: never prefer an expected regression merely for more information."""
    if not is_legal(candidate) or not is_legal(alternative):
        raise ValueError(f"illegal cell: {candidate!r} vs {alternative!r}")
    return (
        candidate[1] == "regressed"
        and alternative[1] != "regressed"
        and _I_RANK[candidate[2]] > _I_RANK[alternative[2]]
    )
