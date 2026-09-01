# Goal and Candidate Contracts

DopaKernel keeps one authoritative `.dopa/goal.json` per workspace. Agents do
not edit it directly; `kernel/decide.py` owns transitions and atomic writes.
Create input JSON under `/tmp` so goal framing is visible without granting an
exemption to production files.

## Goal input

```json
{
  "objective": "Implement the requested behavior without changing the public API",
  "imp": 3,
  "constraints": ["Preserve backward compatibility"],
  "requirements": [
    {
      "id": "focused-tests",
      "text": "The regression test passes",
      "priority": 5,
      "verify": {
        "kind": "command",
        "command": "python3 -m unittest tests.test_regression -v",
        "expect_exit": 0,
        "output_contains": "OK",
        "level": "independent"
      }
    },
    {
      "id": "documentation",
      "text": "The public guide explains the new behavior",
      "priority": 3,
      "verify": {
        "kind": "file",
        "path": "README.md",
        "contains": ["New behavior"],
        "level": "independent"
      }
    }
  ]
}
```

`objective`, requirement IDs, constraints, importance, and verifier definitions
are frozen when `decide.py start` succeeds. An active goal cannot be replaced.
A completed goal may be replaced and receives clean attempts and closed paths.

Verifier kinds:

- `command`: run exactly `command` in the goal workspace, require `expect_exit`
  (default `0`), and optionally require `output_contains`. Only recognized
  read-only test, lint, type-check, status/diff, and inert probe commands are
  accepted; a mutating or unknown command cannot hide behind `verify`.
- `file`: read `path` and require every string in `contains`.

The declared verifier level must meet the goal's importance floor:
`observed` for 1-2, `independent` for 3, and `held-out` for 4-5. A label is a
contract assertion, not proof of true independence; high-stakes framing must
make the verifier's independence concrete and user-visible.

## Candidate input

```json
{
  "candidates": [
    {
      "id": "minimal-fix",
      "requirement_id": "focused-tests",
      "what": "Add the failing case and make the smallest implementation change",
      "in_frame": true,
      "expected_r": "advanced",
      "expected_i": "decision-constraining",
      "cost": 2,
      "confidence": 4,
      "failure_recoverable": true,
      "uncertainty_reducible": false,
      "decision_critical_uncertainty": false,
      "restores_regression": false
    }
  ]
}
```

All booleans must be real JSON booleans. `cost` and `confidence` are integers
from 1 to 5. `expected_r` is `advanced`, `neutral`, or `regressed`;
`expected_i` is `decision-changing`, `decision-constraining`, or `none`.

Selection is a partial order, not one dopamine score:

1. exclude closed, out-of-frame, and regressing candidates;
2. restore known regressions when a restoration candidate exists;
3. focus the highest-priority unmet requirement;
4. prefer recoverable credible progress;
5. use `reduce-first` only for reducible, decision-critical uncertainty when no
   credible progress action dominates it.

## Evidence freshness

Every authorized production mutation increments `mutation_generation`. A
receipt only counts when its generation equals the current generation, its
verifier identity still matches the frozen verifier, it passed, and its level
meets `imp`. This deliberately means work on a later requirement can stale an
earlier receipt; final evaluation requires re-running the affected checks.

## Outcome and terminal-blocker inputs

After each selected action, record the three observed channels rather than only
a prose impression:

```json
{
  "delta": "as",
  "r": "advanced",
  "i": "decision-constraining",
  "note": "The focused regression test now passes"
}
```

Run `decide.py outcome /tmp/dopa-outcome.json`. Recording consumes the selected
action, so the next mutation requires a new selection. `r: regressed` creates a
known regression that forces restoration; `r: neutral` plus `i: none` closes a
stalled path. Two consecutive `delta: worse` observations on the same path also
close it.

If completion is genuinely impossible, record both the external reason and the
evidence establishing it:

```json
{
  "reason": "The required upstream API was permanently retired",
  "evidence": "Provider deprecation notice dated 2026-08-31"
}
```

Run `decide.py block /tmp/dopa-blocker.json`, then `decide.py evaluate`.
Inconvenience, repeated failure, or low remaining context is not a terminal
blocker.

## Platform composition

DopaKernel is not a replacement for platform continuation:

- Codex `/goal` persists the objective by thread, injects a strong completion
  audit into continuation turns, accounts usage, and exposes user lifecycle
  controls. DopaKernel adds deterministic semantic next-action and receipt rules
  rather than copying that loop.
- Claude `/goal` uses a prompt-based Stop-hook loop and a separate small model,
  but its evaluator cannot call tools and judges only the conversation.
  DopaKernel's Stop hook reads frozen-verifier receipts instead of transcript
  summaries.

Keep both layers on the same user objective. Editing, pausing, clearing, or
replacing a platform goal must not silently rewrite an unfinished Dopa contract.
