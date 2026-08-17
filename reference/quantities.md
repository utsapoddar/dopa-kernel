# Quantities — `r`, `i`, `δ[target]`

> **Status: design documentation.** Not loaded at activation. The
> always-active kernel in `SKILL.md` carries the safety-critical rules;
> the phase modules in `modules/` carry the procedures. Read this only
> when a module directs you to, or when a genuine classification
> dispute arises.

Three quantities, kept separate. No scalar exchange rate exists between them,
and none may be invented.

## `r` — verified compliant progress

Progress toward the envelope `C`, inside the envelope, evidenced rather than
asserted. What counts as evidence is domain-specific (the selected file under
`modules/`); the
standard is the same everywhere: an unverified change scores `r = 0` however
busy the work looked.

- `r > 0`: a stated requirement moves to met-with-evidence, or a verified
  deficiency is removed, with nothing else made worse.
- `r = 0`: requirement-relevant state is unchanged.
- `r < 0`: a previously satisfied requirement fails, a prohibition is grazed,
  a committed decision is silently reversed, or something the work touched is
  left worse than it started.

## `i` — decision-relevant information gain

`i > 0` only when a named observation changes the next action, removes a live
alternative, or materially changes a stated prediction. Information that
changes the next action, removes a live alternative, or materially changes a
prediction is the *only* information that counts; everything else scores
`i = 0` no matter how much was read. This decision-relevance rule is the
procrastination guard, built into the definition.

`i` is a reviewed judgment, not observed ground truth.
`i` can never close the gate: you cannot finish by learning things.

## `δ[target]` — typed ordinal prediction error

Predictions are prospective: each one is stated before acting, never after.
State `expect[r]: ...` (advance / neutral / regress plus the expected
observable) and, only when material, `expect[i]: ...`. Afterward compare each
prediction with its own target:

- **better than expected** — observed class higher than predicted;
- **as expected** — same class and observable;
- **worse than expected** — lower class or mismatched observable.

Record `δ[r]` and `δ[i]` separately when both were predicted; never merge
incomparable outcomes into one reading. A missing prediction makes that `δ`
unscorable — record `δ: unscorable` and never reconstruct it from hindsight.
A `δ` written after the outcome without a prior `expect` is not a calibration
reading; it is a story about the past. The TD equation behind `δ` is
conceptual only; no `V(s)`, `γ`, or numeric error is ever computed.

## Policy table

This is a policy table — it selects the next action; it does not define or
re-weight `r` or `i` (their classification frame is `matrix.md`).

| | `r > 0` | `r = 0 ∧ i > 0` | `r = 0 ∧ i = 0` | `r < 0` |
|---|---|---|---|---|
| **better than expected** | Extend the method; raise pace | Apply the information to the next choice; recalibrate its expected value | No value occurred: restate the prediction before continuing | Restore the prior state; retain any information reading separately |
| **as expected** | **Calibrated advance.** Proceed with minimal ceremony | **Calibrated information gain.** Use it; this is not a stall | **Stall.** Change approach or re-check the goal | Restore or repair before pursuing further improvement |
| **worse than expected** | Advancing but mispredicted — recalibrate and continue | Use what was learned, but recalibrate the information method | **Failure.** Escalate | Restore or roll back; escalate if recurrence shows the method is unsafe |

Only `as expected ∧ r = 0 ∧ i = 0` is a stall. Expected progress or expected
decision-relevant information produces `δ ≈ 0` while still being useful; low
surprise is not low value. A regression is handled explicitly, never hidden in
the no-progress column.

## Pacing and the anti-recursion rule

Tonic pacing is phase-aware and tracks two channels without summing them: the
verified `r` rate, and whether recent `i` converted into an action or removed
a live alternative.

- High `r` rate → move fast with minimal ceremony.
- Low `r` plus new decision-relevant `i` → spend the next unit applying that
  information, not gathering more by default.
- Low `r` and no new `i` → slow down; pick one bounded observation or a
  different approach.
- Repeated information-only outcomes without subsequent progress → an
  information loop; act, test, or surface the unresolved choice instead of
  researching again.

**Precedence over the tie-break:** while unapplied `i` remains, the next unit
must apply or test it. The tie-break is not consulted to justify gathering
additional information. Only after no unapplied `i` remains may the matrix
tie-break rank a new incomparable `(r, i)` choice.
