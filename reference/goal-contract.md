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
A completed, impossible, or explicitly user-cancelled goal may be replaced and
receives clean attempts and closed paths.

Verifier kinds:

- `command`: parse `command` into an argument vector and run it without a shell
  in the goal workspace, require `expect_exit`
  (default `0`), and optionally require `output_contains`. Only recognized
  read-only test, lint, type-check, status/diff, and inert probe commands are
  accepted; shell substitution, a mutating command, or an unknown command cannot
  hide behind `verify`. A verifier that changes the workspace fails and advances
  the mutation generation.
- `file`: read `path` and require every string in `contains`.
  A file verifier cannot target `.dopa/` controller state.

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
      "failure_recoverable": true
    }
  ]
}
```

`id`, `requirement_id`, `expected_r`, `expected_i`, `cost` and `confidence` are
required. `cost` and `confidence` are integers from 1 to 5. `expected_r` is
`advanced`, `neutral`, or `regressed`; `expected_i` is `decision-changing`,
`decision-constraining`, or `none`.

**Write only the booleans that are true.** The five boolean fields —
`in_frame`, `failure_recoverable`, `uncertainty_reducible`,
`decision_critical_uncertainty`, `restores_regression` — each default to
`false`, so omitting one is identical to writing it as `false`. The example
above omits the three that do not apply. When present, a boolean must be a real
JSON boolean, not a string or number.

Omission is never a way to *assert* something. `in_frame` defaults to `false`
and out-of-frame candidates are excluded from selection, so an in-frame
candidate still has to say so.

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
Finalization also re-runs every recorded verifier so editing a receipt cannot
manufacture completion. Tool hooks reject direct access to `.dopa`; controller
state transitions must go through exact `decide.py` commands.

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
  "evidence": {
    "kind": "file",
    "path": "evidence/provider-deprecation.txt",
    "contains": ["permanently retired"]
  }
}
```

Run `decide.py block /tmp/dopa-blocker.json`, then `decide.py evaluate`.
The evidence file is verified when recorded and again when finalizing. A known
regression or unobserved mutation must be resolved first. Inconvenience,
repeated failure, controller state under `.dopa`, or low remaining context is
not terminal-blocker evidence.

If the user changes the objective, use a distinct authorized cancellation:

```json
{
  "reason": "The user replaced the requested objective"
}
```

Run `decide.py cancel /tmp/dopa-cancel.json`, then start the replacement goal.
With the Claude hooks installed, `cancel` and `block` return the platform's
native `permissionDecision: "ask"`, which still forces a user prompt in auto
mode. Direct CLI use is an operator action; on platforms without that hook,
invoke either transition only after the user's explicit instruction. Never
infer authorization or use cancellation to escape unfinished work.
