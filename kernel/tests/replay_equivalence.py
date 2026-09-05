#!/usr/bin/env python3
"""Protocol-change equivalence replay.

Drives identical command sequences through a baseline checkout and the working
tree, then asserts the kernel decided the same thing both times:

    exit codes             identical, per command
    final .dopa/goal.json  identical, modulo wall-clock timestamps

Display output is deliberately excluded from the comparison; shrinking it is
the point. The tool reports the stdout delta so the saving is measured rather
than asserted.

    python3 kernel/tests/replay_equivalence.py [baseline-ref]

Exits non-zero if any scenario diverges.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

KERNEL = Path(__file__).resolve().parents[1]
REPO = KERNEL.parent
TIMESTAMP = re.compile(r"^\d{4}-\d{2}-\d{2}T[\d:.+\-]+$")


def _goal(objective="Create the artifact", imp=2):
    return {
        "objective": objective, "imp": imp, "constraints": [],
        "requirements": [
            {"id": "artifact", "text": "Artifact is correct", "priority": 5,
             "verify": {"kind": "file", "path": "artifact.txt",
                        "contains": ["done"], "level": "observed"}},
            {"id": "notes", "text": "Notes explain the artifact", "priority": 3,
             "verify": {"kind": "file", "path": "notes.txt",
                        "contains": ["why"], "level": "observed"}},
        ],
    }


def _candidate(cid, rid="artifact", **over):
    base = {"id": cid, "requirement_id": rid, "what": f"do {cid}",
            "in_frame": True, "expected_r": "advanced", "expected_i": "none",
            "cost": 1, "confidence": 4, "failure_recoverable": True,
            "uncertainty_reducible": False, "decision_critical_uncertainty": False,
            "restores_regression": False}
    base.update(over)
    return base


def _outcome(r="advanced", i="decision-constraining", delta="as", note="moved"):
    return {"delta": delta, "r": r, "i": i, "note": note}


# Each scenario is a list of steps. A step is (argv, input_json_or_None) plus an
# optional workspace mutation, so attempts accumulate past SWITCH_AFTER and the
# status trim is exercised on real history rather than an empty list.
def _scenarios():
    long_history = [(["start"], _goal())]
    for n in range(6):
        long_history.append((["select"], {"candidates": [_candidate(f"path-{n}")]}))
        long_history.append((["outcome"], _outcome(
            r="neutral" if n % 3 == 2 else "advanced",
            i="none" if n % 3 == 2 else "decision-constraining")))
        long_history.append((["status"], None))
    long_history.append((["evaluate"], None))

    stall_closes_path = [
        (["start"], _goal(objective="Stall then close")),
        (["select"], {"candidates": [_candidate("stalls")]}),
        (["outcome"], _outcome(r="neutral", i="none")),
        (["status"], None),
        (["select"], {"candidates": [_candidate("stalls")]}),   # now closed
        (["status"], None),
    ]

    two_worse_closes_path = [
        (["start"], _goal(objective="Two worse observations")),
        (["select"], {"candidates": [_candidate("wobbles")]}),
        (["outcome"], _outcome(delta="worse")),
        (["select"], {"candidates": [_candidate("wobbles")]}),
        (["outcome"], _outcome(delta="worse")),
        (["status"], None),
        (["select"], {"candidates": [_candidate("wobbles")]}),
        (["status"], None),
    ]

    regression_forces_restore = [
        (["start"], _goal(objective="Regress then restore")),
        (["select"], {"candidates": [_candidate("breaks")]}),
        (["outcome"], _outcome(r="regressed", note="broke the build")),
        (["status"], None),
        (["select"], {"candidates": [_candidate("unrelated"),
                                     _candidate("restores", restores_regression=True)]}),
        (["outcome"], _outcome(r="advanced")),
        (["status"], None),
    ]

    verify_and_complete = [
        (["start"], _goal(objective="Verify both requirements")),
        (["evaluate"], None),
        (["verify"], "artifact"),
        (["write-file"], ("artifact.txt", "done\n")),
        (["verify"], "artifact"),
        (["write-file"], ("notes.txt", "why it exists\n")),
        (["verify"], "notes"),
        (["status"], None),
        (["evaluate"], None),
    ]

    blocked = [
        (["start"], _goal(objective="Externally blocked")),
        (["write-file"], ("notice.txt", "permanently retired\n")),
        (["block"], {"reason": "upstream retired",
                     "evidence": {"kind": "file", "path": "notice.txt",
                                  "contains": ["permanently retired"]}}),
        (["status"], None),
        (["evaluate"], None),
    ]

    return {
        "long_history": long_history,
        "stall_closes_path": stall_closes_path,
        "two_worse_closes_path": two_worse_closes_path,
        "regression_forces_restore": regression_forces_restore,
        "verify_and_complete": verify_and_complete,
        "blocked": blocked,
    }


def _normalise(value, work: Path | None = None):
    """Drop wall-clock timestamps and the per-run workspace path.

    Both vary between two runs of identical code, so leaving them in would
    report a divergence on every scenario. Everything else must match exactly.
    """
    if isinstance(value, dict):
        return {k: _normalise(v, work) for k, v in value.items()}
    if isinstance(value, list):
        return [_normalise(v, work) for v in value]
    if isinstance(value, str):
        if TIMESTAMP.match(value):
            return "<timestamp>"
        if work:
            for form in (str(work.resolve()), str(work)):
                value = value.replace(form, "<workspace>")
    return value


def run_scenario(cli: Path, steps) -> dict:
    work = Path(tempfile.mkdtemp())
    exits, stdout_bytes = [], 0
    try:
        for i, (argv, payload) in enumerate(steps):
            if argv[0] == "write-file":
                name, body = payload
                (work / name).write_text(body)
                continue
            args = list(argv)
            if isinstance(payload, str):
                args.append(payload)
            elif payload is not None:
                path = work / f"in-{i}.json"
                path.write_text(json.dumps(payload))
                args.append(str(path))
            done = subprocess.run([sys.executable, str(cli), *args], cwd=work,
                                  capture_output=True, text=True)
            exits.append((" ".join(argv), done.returncode))
            stdout_bytes += len(done.stdout)
        state_file = work / ".dopa" / "goal.json"
        state = json.loads(state_file.read_text()) if state_file.exists() else None
        return {"exits": exits, "state": _normalise(state, work),
                "stdout_bytes": stdout_bytes}
    finally:
        shutil.rmtree(work, ignore_errors=True)


def main(argv):
    ref = argv[0] if argv else "main"
    base = Path(tempfile.mkdtemp()) / "baseline"
    add = subprocess.run(["git", "worktree", "add", "--detach", str(base), ref],
                         cwd=REPO, capture_output=True, text=True)
    if add.returncode != 0:
        print(f"could not create baseline worktree at {ref}:\n{add.stderr}", file=sys.stderr)
        return 2
    try:
        base_cli = base / "kernel" / "decide.py"
        head_cli = KERNEL / "decide.py"
        failures, before, after = [], 0, 0

        for name, steps in _scenarios().items():
            b = run_scenario(base_cli, steps)
            h = run_scenario(head_cli, steps)
            before += b["stdout_bytes"]
            after += h["stdout_bytes"]

            if b["exits"] != h["exits"]:
                failures.append(f"{name}: exit codes diverged\n"
                                f"  baseline {b['exits']}\n  current  {h['exits']}")
            if b["state"] != h["state"]:
                failures.append(f"{name}: final state diverged")
                for key in sorted(set((b["state"] or {})) | set((h["state"] or {}))):
                    bv, hv = (b["state"] or {}).get(key), (h["state"] or {}).get(key)
                    if bv != hv:
                        failures.append(f"    {key}:\n      baseline {json.dumps(bv)[:400]}\n"
                                        f"      current  {json.dumps(hv)[:400]}")
            status = "DIVERGED" if (b["exits"] != h["exits"] or b["state"] != h["state"]) else "ok"
            delta = (b["stdout_bytes"] - h["stdout_bytes"]) / b["stdout_bytes"] * 100 \
                if b["stdout_bytes"] else 0.0
            print(f"{name:<28} {status:<9} stdout {b['stdout_bytes']:>7} -> "
                  f"{h['stdout_bytes']:>7} ({delta:+.1f}%)")

        print()
        if failures:
            print("DECISION EQUIVALENCE FAILED\n")
            print("\n".join(failures))
            return 1
        saved = (before - after) / before * 100 if before else 0.0
        print(f"decisions identical across {len(_scenarios())} scenarios "
              f"(exit codes + final state)")
        print(f"stdout {before:,} -> {after:,} bytes ({saved:+.1f}%, "
              f"~{(before - after) / 4:,.0f} tokens saved per full replay)")
        return 0
    finally:
        subprocess.run(["git", "worktree", "remove", "--force", str(base)],
                       cwd=REPO, capture_output=True)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
