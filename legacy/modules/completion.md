# Procedure — completion gate

Invoked from the router **unconditionally** before any final response or
completion claim. Elaborates K5; never waives it. If this module cannot be
read, K5 still binds: no completion claim without fresh evidence for every
envelope item.

The gate evaluates the **current verified state**, not a sum of earlier
progress — later regressions undo earlier gains — and `i` never closes the gate.
You cannot finish by learning things.

## Three conditions, all required

1. **Compliance verified.** Walk every envelope item individually with the
   domain adapter's evidence standard. Asserted ≠ evidenced. Evidence is an
   observation and **never a self-report**: "I checked it" is an assertion, and
   so is a remembered count. **A manual count is an assertion**, not evidence.
2. **No known-worse state.** Every stated requirement can be met while
   something nobody thought to prohibit is left broken. Nothing the work
   touched may be worse than it started. A state change needs a captured prior state,
   a prepared rollback, and verification; if it regressed state,
   verified restoration is required, and failed restoration fails this
   condition outright (`rollback.md`).
3. **Marginal value below threshold.** Name the single highest-value remaining
   improvement inside the envelope. Concrete and worth its cost → iterate.
   Vague, trivial, or outside the envelope → stop. Once mechanical constraints
   are verified, the highest-value remaining improvement is a substantive one —
   stronger reasoning, a sharper decision, a more robust implementation — not
   re-verification of already-evidenced items.

**The asymmetry is the mechanism:** you cannot stop by asserting "good enough", and you cannot continue by asserting "could be better". Both
directions require naming something specific.

## Stakes raise the gate

At `imp` ≥ 4 — frozen with the envelope under K1, see `reference/matrix.md` 8c
— two further conditions bind:

4. **Re-verified at the gate.** Every item is observed again here, never
   carried forward from earlier in the session. An observation taken before the
   gate has become a recalled one by the time the claim is made.
5. **No asserted items.** An item that lands asserted-not-evidenced
   fails the gate outright: surface it and stop. Never claim completion with
   the gap noted alongside it.

At `imp` ≤ 3 both remain good practice and neither blocks.

## The ledger

Write the walk in the process channel — never in the deliverable — with
one line per envelope item in the form `item → evidence`, citing the observation
rather than the intention. The final line names the single highest-value
remaining improvement and the decision: iterate, or stop with the reason
(vague, trivial, or outside the envelope).

Re-verify after any edit: a measurement taken before a later change no longer
evidences anything. If a verification path is denied, try another observation
path before any fallback; if none exists, mark the item
asserted-not-evidenced, say why, and surface it rather than claiming
completion.

## Before responding

Check K6 one last time: under an output restriction, the reply carries the
deliverable and nothing else — no ledger, envelope, `expect`, `δ`, or proposal
text. If the reply is unrestricted, only the concise authorization question
permitted by `proposal.md` may follow; process records still never do.
