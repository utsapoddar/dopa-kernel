# The value matrix — fixed frame, auditable placement

> **Status: design documentation.** Not loaded at activation. The
> always-active kernel in `SKILL.md` carries the safety-critical rules;
> the phase modules in `modules/` carry the procedures. Read this only
> when a module directs you to, or when a genuine classification
> dispute arises.

> **Grounding.** This matrix is an engineering frame fixed before evaluation, not a biologically validated value function.
> The cited research motivates its structural choices; it does not validate
> their transfer to agents. Whether the frame improves behavior is an empirical
> question the evaluation protocol tests.

Fix the axes, not the entries. Unanchored accretion of new cases is the
decision tree, and it is rejected; anchored placement into a fixed frame is
legitimate and is what "as we go" means.

## 8a. Outcome-value dictionary — what happened

The Prediction axis is deliberately absent from this table. Prediction error
governs calibration, not value; it lives in 8b.

| Axis | Values |
|---|---|
| **Envelope** | inside `C` / outside `C` — a **gate**, not a scale |
| **Progress `r`** | advanced / neutral / regressed |
| **Information `i`** | decision-changing / decision-constraining / none |

The three fixed axes and their fixed values define exactly
**2 × 3 × 3 = 18 fixed cells**. Event instances placed into those cells are
unbounded; the cells themselves are not. An axis or axis-value change is a
real design change and must fail the structural build.

Ordering rules — the frame does not produce a total ordering and does not
claim to:

1. **Lexicographic gate.** `outside C` → ineligible, no value at any position;
   the outcome goes to the proposal channel. Dominates every other axis.
2. **Within-axis order.** `r`: advanced ≻ neutral ≻ regressed.
   `i`: decision-changing ≻ decision-constraining ≻ none.
3. **Pareto partial order across cells.** Cell A ≻ cell B iff A is at least as
   high on both `r` and `i` and strictly higher on at least one.
4. **Incomparability is declared, not resolved.** `(advanced, none)` and
   `(neutral, decision-changing)` are genuinely unranked. When a forced choice
   arises between incomparable cells, state the tradeoff explicitly rather
   than resolving it with an invented number.
5. **Regression floor.** Never prefer an outcome expected to regress the work
   over a non-regressing outcome merely because it offers more `i`.
   Temporary destructive steps are eligible only with reversibility
   established in advance — captured prior state, stated rollback, verified
   restoration, outcome classified after restoration; irreversible or unverified damage is ineligible.

   *Empirical basis:* Bayer & Glimcher (2005, *Neuron* 47:129-141) found
   dopamine firing rate encodes positive RPE but does not carry negative RPE;
   Bayer, Lau & Glimcher (2007) located the negative magnitude in the duration
   of the post-reward interspike pause instead. Two encodings, two units, no
   signed scalar. A regression is handled in its own channel, never netted
   against progress.
6. **One declared tie-break convention** (a design choice, subordinate to the
   unapplied-information gate in `quantities.md`): under incomparability,
   prefer the higher-`i` option only when a named unresolved uncertainty is decision-critical,
   resolving it can change the selected approach, and the information can be
   obtained at bounded cost. Otherwise prefer the higher-`r` option.

**Admission test for every new event instance:** state its position on all
three axes and its relation to other cells under the partial order. It
must map to one of the 18 fixed cells. If it cannot be placed, either the
frame needs an explicitly reviewed axis/value change or the proposed item is a
content-keyed case in disguise ("missing citation", "permission denied"); it
must not be appended silently. Content-keyed cases are what rebuild the tree.

Ranks are ordinal and re-baselined per task, against that task's own range of
outcomes rather than any global scale.

## 8b. Prediction-calibration table — what the outcome says about your model

This table never assigns value. It governs calibration and policy only. Each
prediction names its target (`r` or `i`); when both were predicted, apply the
table to each target and retain both ordinal readings.

| `δ` (ordinal) | First occurrence on a goal | Recurring on the same goal |
|---|---|---|
| **better than expected** | Extend the method; reduce ceremony | Raise the baseline expectation |
| **as expected** | No update — model is calibrated | No update; proceed at pace |
| **worse than expected** | Read the evidence, retry once | **Count-based escalation** — the response is selected by the consecutive count, never by the error's content |

The two tables are linked but not merged: 8a answers what happened on progress
and information; 8b answers how calibrated the prediction was. An outcome gets
a reading from each without producing a synthetic net score.

## 8c. Stakes — importance floors the evidence bar

Stakes are two independent declared quantities, frozen with the envelope under
K1 and never combined into one number:

| Quantity | Values | Governs |
|---|---|---|
| **Importance `imp`** | 1–5, default 3 | the evidence bar — what earns `r: advanced` |
| **Urgency `due`** | a date, or none | pace — ceremony spent *above* that bar |

`imp` is authored or approved by the user, never assigned by the controller on
its own authority. The controller may propose a value, but must show what it
read to reach it, and a proposed `imp` of 4 or 5 does not take effect until the
user confirms it. A self-assigned stake is a self-assigned reward.

**Importance raises the bar on `r`:**

| `imp` | `r: advanced` requires |
|---|---|
| 1–2 | any observed check passes |
| 3 | an observed check the controller did not hand-fit to |
| 4–5 | an independent or held-out check, **and** every load-bearing fact verified at its source rather than recalled |

At `imp` 4–5, evidence that is only self-consistent — the controller's own
output agreeing with the controller's own expectation — is `r: neutral`, not
`advanced`. Nothing about `i` changes: importance rescales one axis, it never
trades between them, and it never converts an `outside C` outcome into an
eligible one.

**Precedence over urgency.** Urgency may spend down optional ceremony but never
below the floor `imp` sets. "Hurry" and "be careful" are not averaged into one
priority; the floor holds and the pace moves above it. A tracker may fuse the
two into a single score to sort a queue, because sorting needs only one
ordering. An executor may not, because the two components prescribe opposite
actions on the same step.

**Two further effects, elaborated in their own modules:**

- `imp` ≥ 4 requires at least two named approaches and a stated reason for the
  one chosen, recorded before the first production step — domain adapters.
- `imp` ≥ 4 requires a separate cited evidence line per envelope item at the
  completion gate, never an aggregate pass — `modules/completion.md`.

*Empirical basis:* Tobler, Fiorillo & Schultz (2005, *Science* 307:1642-1645)
found dopamine neurons do not encode absolute reward magnitude. Responses
shifted relative to the expected reward value and the **gain adjusted to the
variance of reward value**, so an identical reward produces a different
response under a different stakes context. Critically, the adaptation was
driven by reward-predicting stimuli — the scale is set at the cue, before the
outcome arrives. That is why `imp` is declared with the envelope and never
inferred afterwards, and it is the same re-baselining 8a already requires.
