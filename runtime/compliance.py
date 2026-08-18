#!/usr/bin/env python3
"""Passive routing-compliance instrumentation for DopaKernel.

Scans existing session transcripts and reports how often each routing rule was
followed, counting only sessions that had an *opportunity* to follow it. No
probes are consumed and no session content is recorded — the report carries
counts, rates, and session identifiers only.

Usage:
    python3 compliance.py [TRANSCRIPT_DIR ...]      # defaults to ~/.claude/projects
    python3 compliance.py --json                    # machine-readable
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kernel_state  # noqa: E402
from gate_pretooluse import is_scratch  # noqa: E402

GATES = ("adapter", "rollback", "proposal", "completion", "cell_emission")


def assess(state) -> dict:
    """Per-gate {opportunity, compliant} for one session. {} if kernel inactive."""
    if not state.active:
        return {}
    first_mutation = state.first_mutation_at()
    real = [m for m in state.mutations if not is_scratch(m[2])]
    first_real = real[0][0] if real else None
    outside = [idx for idx, axis, value in state.cells
               if axis == "C" and value == "outside"]

    adapter_at = None
    adapter = state.domain_adapter()
    if adapter is not None:
        adapter_at = state.modules_read[adapter]

    rollback_at = state.modules_read.get("rollback.md")
    proposal_at = state.modules_read.get("proposal.md")
    completion_at = state.modules_read.get("completion.md")

    return {
        "adapter": {
            "opportunity": True,
            "compliant": adapter_at is not None
            and (first_mutation is None or adapter_at < first_mutation),
        },
        "rollback": {
            "opportunity": first_real is not None,
            "compliant": (rollback_at is not None and rollback_at < first_real)
            if first_real is not None else None,
        },
        "proposal": {
            "opportunity": bool(outside),
            "compliant": (proposal_at is not None and proposal_at >= min(outside))
            if outside else None,
        },
        "completion": _completion_per_turn(state),
        "cell_emission": {
            "opportunity": True,
            "compliant": bool(state.cells),
        },
    }


def _completion_per_turn(state) -> dict:
    """Each turn-end is an opportunity; a turn gates if completion.md was read
    inside its own window. Assessing a many-turn session against only its last
    turn would mark a session that gated ten times as a single miss."""
    turns = state.user_turns or [0]
    all_reads = state.all_module_reads.get("completion.md", [])
    gated = 0
    for i, start in enumerate(turns):
        end = turns[i + 1] if i + 1 < len(turns) else float("inf")
        if any(start <= r < end for r in all_reads):
            gated += 1
    return {"opportunity": True, "turns": len(turns), "gated": gated,
            "compliant": gated == len(turns)}


def aggregate(rows: list[dict]) -> dict:
    """Rates over opportunities only; a gate with no opportunity has rate None."""
    out: dict = {}
    for row in rows:
        for gate, verdict in row.items():
            slot = out.setdefault(gate, {"opportunities": 0, "compliant": 0})
            if "turns" in verdict:
                # per-turn gate: every turn-end is its own opportunity
                slot["opportunities"] += verdict["turns"]
                slot["compliant"] += verdict["gated"]
            elif verdict["opportunity"]:
                slot["opportunities"] += 1
                if verdict["compliant"]:
                    slot["compliant"] += 1
    for slot in out.values():
        n = slot["opportunities"]
        slot["rate"] = (slot["compliant"] / n) if n else None
    return out


def scan(roots: list[str]) -> dict:
    sessions = []
    for root in roots:
        for path in sorted(Path(root).rglob("*.jsonl")):
            state = kernel_state.parse(str(path))
            if not state.active:
                continue
            verdicts = assess(state)
            sessions.append({
                "session": path.stem,
                "records": state.records,
                "gates": verdicts,
            })
    return {
        "sessions_scanned": len(sessions),
        "sessions": sessions,
        "aggregate": aggregate([s["gates"] for s in sessions]),
    }


def _render(report: dict) -> str:
    lines = [f"DopaKernel routing compliance — {report['sessions_scanned']} active session(s)", ""]
    agg = report["aggregate"]
    if not agg:
        lines.append("no kernel sessions found")
        return "\n".join(lines)
    lines.append(f"{'gate':<15}{'opportunities':>14}{'compliant':>11}{'rate':>8}")
    lines.append("-" * 48)
    for gate in GATES:
        slot = agg.get(gate)
        if not slot:
            continue
        rate = "n/a" if slot["rate"] is None else f"{slot['rate'] * 100:.0f}%"
        lines.append(f"{gate:<15}{slot['opportunities']:>14}{slot['compliant']:>11}{rate:>8}")
    lines += ["", "per session:"]
    for s in report["sessions"]:
        flags = []
        for gate in GATES:
            v = s["gates"].get(gate) or {}
            if not v.get("opportunity"):
                flags.append(f"{gate}=-")
            else:
                flags.append(f"{gate}={'ok' if v['compliant'] else 'MISS'}")
        lines.append(f"  {s['session'][:8]}  ({s['records']:>5} rec)  " + "  ".join(flags))
    lines += [
        "",
        "coverage limits — read these before trusting the rates:",
        "  * state changes made through Bash (git, rm, shell redirects) are NOT",
        "    counted as mutations, so `rollback` under-reports opportunities.",
        "  * `proposal` only has an opportunity when a session emits",
        "    `cell[C]: outside`; an undeclared excursion is invisible here.",
        "  * `completion` counts every turn-end as an opportunity.",
    ]
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    as_json = "--json" in argv
    roots = [a for a in argv if not a.startswith("--")]
    if not roots:
        roots = [str(Path.home() / ".claude" / "projects")]
    report = scan(roots)
    print(json.dumps(report, indent=2) if as_json else _render(report))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
