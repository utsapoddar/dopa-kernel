# Procedure — stall or replan

Invoked from the router when a unit of work produced no verified progress, or
when information-only outcomes repeat. Elaborates the kernel's pacing; creates
no new prohibition.

## Read the outcome first

Classify what actually happened on progress and information, separately, then
use the typed prediction reading to update expectations. This selects the next
action; it does not redefine `r` or `i`.

| | `r > 0` | `r = 0 ∧ i > 0` | `r = 0 ∧ i = 0` | `r < 0` |
|---|---|---|---|---|
| **better than expected** | Extend the method; raise pace | Apply the information to the next choice; recalibrate its expected value | No value occurred: restate the prediction before continuing | Restore the prior state; retain any information reading separately |
| **as expected** | **Calibrated advance.** Proceed with minimal ceremony | **Calibrated information gain.** Use it; this is not a stall | **Stall.** Change approach or re-check the goal | Restore or repair before pursuing further improvement |
| **worse than expected** | Advancing but mispredicted — recalibrate and continue | Use what was learned, but recalibrate the information method | **Failure.** Escalate | Restore or roll back; escalate if recurrence shows the method is unsafe |

Only `as expected ∧ r = 0 ∧ i = 0` is a stall. Expected progress or expected
decision-relevant information produces `δ ≈ 0` while still being useful; low
surprise is not low value. A regression is handled explicitly, never hidden in
the no-progress column — go to `rollback.md`.

## Anti-recursion

- High `r` rate → move fast with minimal ceremony.
- Low `r` plus new decision-relevant `i` → spend the next unit **applying**
  that information, not gathering more.
- Low `r` and no new `i` → slow down; pick one bounded observation or a
  different approach.
- Repeated information-only outcomes without subsequent progress → an
  **information loop**; act, test, or surface the unresolved choice instead of
  researching again.

While unapplied `i` remains, the next unit must apply or test it. No tie-break
may be used to justify gathering more information.

## Escalating a repeated worse-than-expected outcome

**Count-based escalation**: the response is selected by the consecutive count
of worse-than-expected outcomes on this goal, **never by the error's content**,
so no branch grows with the number of distinct errors seen.

1. Read the evidence actually returned; retry the same justified action once.
2. Make one bounded **observation** of real state. Parameter-tweaking is not an
   observation and is not permitted at this rung.
3. Re-model the assumption the evidence falsified, and say which one it was.
4. Surface the blocker: what was attempted, what the evidence showed, what safe
   paths remain, and what input is needed.

If the falsified assumption is about product code rather than environment or
tooling, hand off to a debugging procedure rather than continuing here.

## Exit

Return to the domain adapter with the chosen next action, or, if the goal
itself is in doubt and a better course lies outside the envelope, go to
`proposal.md` — never adopt it silently.
