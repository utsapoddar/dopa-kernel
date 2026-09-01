---
name: dopa-kernel
description: Use only when the user explicitly says `Dopa mode` or invokes `dopa-kernel`.
---

# DopaKernel

Prevent premature victory by keeping the objective stable, choosing work from
semantic task state, and requiring fresh evidence from outside the final prose.

> Dopa mode: persist until every stated requirement has current evidence, or a
> real external blocker makes the objective impossible.

The controller is `kernel/decide.py` beside this file. Invoke it with its
absolute path; the current directory must remain the target workspace.

## 1. Frame a durable goal

**Frame.** Translate the user's exact objective into a visible goal contract:
requirements, constraints, `imp: 1-5`, and a frozen verifier per requirement.
Do not silently broaden, narrow, or substitute the objective. At `imp 4-5`,
show the evidence bar and wait for the user's agreement.

Write the input as `/tmp/dopa-goal.json`, then run:

```text
python3 <dopa-kernel>/kernel/decide.py start /tmp/dopa-goal.json
```

An unfinished goal cannot be overwritten. See `reference/goal-contract.md`.
If the user explicitly cancels or reframes it, record that authorization with
`decide.py cancel /tmp/dopa-cancel.json`; do not misuse `impossible` to pivot.

## 2. Select the next semantic action

Enumerate candidates tied to one unmet `requirement_id`. Each candidate declares
envelope membership, expected `r` and `i`, confidence, bounded cost,
recoverability, and whether reducible uncertainty is decision-critical. Write
them to `/tmp/dopa-candidates.json`, then run `decide.py select` on that file.

You infer candidate fields; you do not pick the winner. The policy applies hard
constraints and requirement priority first. Credible progress beats research.
`reduce-first` is valid only when uncertainty could change the action choice.
An out-of-frame idea is a proposal, never a substitution.
If no candidate serves the globally highest-priority unmet requirement, add or
reframe candidates instead of silently working on a lower-priority requirement.

## 3. Run one prediction-error cycle

1. **Predict.** State `expect:` for the selected action.
2. **Act.** Make one bounded production mutation.
3. **Observe.** Inspect environment output; prose and remembered counts are not evidence.
4. **Compare.** Record `got:` and keep the readings separate:
   - `r` progress: `advanced / neutral / regressed`
   - `i` information: `decision-changing / decision-constraining / none`
   - `δ` surprise: `better / as / worse`
5. Write `/tmp/dopa-outcome.json` with the observed `r`, `i`, `delta`, and an
   optional `note`; run `decide.py outcome /tmp/dopa-outcome.json` before
   another mutation. The action is consumed, so re-select next.

Never sum them or trade progress for information. No prior `expect` makes `δ`
unscorable. Two genuinely consecutive `worse` outcomes close the path;
re-selection does not erase the history. Restore a known regression first.

## 4. Verify requirements, not confidence

Run `decide.py verify <requirement_id>`. It executes the verifier frozen in the
goal contract and stores a receipt with verifier identity, result, digest,
evidence level, and mutation generation. Any later production mutation makes
older receipts stale, so re-verify them.

Command verifiers run as parsed argument vectors, never through a shell. If a
verifier changes the workspace, it fails and advances the mutation generation.

Importance only raises the minimum evidence level:

- `imp 1-2`: `observed`
- `imp 3`: `independent`
- `imp 4-5`: `held-out`

Urgency never lowers this floor. Information without a passing receipt cannot
complete a requirement.

## 5. Let the evaluator decide completion

Run `decide.py evaluate`. Its terminal verdicts are `met / not_met / impossible`.

- `met`: every requirement has a fresh, sufficiently strong passing receipt,
  survives final live re-verification, and has no known regression.
- `not_met`: continue with the named requirement; re-select when needed.
- `impossible`: stop only for an externally established terminal blocker, never
  because attempts are inconvenient or the context is long. Record its reason
  and a file verifier in `/tmp/dopa-blocker.json`, then run `decide.py block` on
  it. Pending outcomes and known regressions must be resolved first.

Do not declare victory before `met`. Claude's Stop hook enforces this evaluator;
Codex `/goal` can provide durable continuation while this kernel supplies
semantic allocation and evidence policy. Platform `/goal` never overrides the
user-visible Dopa goal contract.

Keep process state in `.dopa/`, never in the deliverable, and never read or edit
it directly; only exact `decide.py` control commands own that state. The legacy
18-cell matrix remains reference material; its semantic dimensions are useful,
but its mandatory module-reading ceremony is not part of this runtime.

The active goal file keeps hooks active in delegated transcripts even when they
do not repeat the original Skill invocation. Completion, impossibility, or an
authorized cancellation ends that durable activation.
