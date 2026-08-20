---
name: dopa-kernel
description: Use only when the user explicitly says `Dopa mode` or invokes `dopa-kernel`.
---

# DopaKernel

A control loop, not a procedure. Six moves. Everything else is reference.

> Dopa mode: Work carefully and persist until the result satisfies every stated requirement.

## Choose the path before framing the work

You do not pick the path. Enumerate the ways you infer could reach the goal —
two or twenty — and score each 1-5 on `cost`, `upside`, `confidence`, plus
whether its failure is **recoverable** and whether its uncertainty is **cheaply
reducible**. Then run `kernel/decide.py select <file>` and do what it returns.
`reduce-first` means go look before building. Guessing the scores is your job;
choosing between them is not, and the gate recomputes the rule from your own
numbers, so a record that claims a different winner is rejected.

After each attempt run `kernel/decide.py outcome better|as|worse`. Two
consecutive `worse` on one path closes it: re-select, do not keep repairing.

## The loop

1. **Frame.** Write what done means, what is off-limits, and `imp`. Once, before acting.
2. **Predict.** Write `expect:` — what you think the next action will produce.
3. **Act.**
4. **Observe.** Run it. Read the output. An observation is something the
   environment produced; an assertion is something you produced. "It should
   work", "the change is complete", and a remembered count are assertions.
5. **Compare.** Write `got:` with the three readings. The gap between `expect`
   and `got` is the entire signal — that gap is the only thing worth tracking.
6. **Never claim done against a failing observation.** If the last thing you ran
   failed, you are not done, however good the rest looks.

## The readings

Keep them separate. Never sum them, never trade one for another.

| | values |
|---|---|
| `r` progress | `advanced` (verified, in-frame) / `neutral` / `regressed` |
| `i` information | `decision-changing` / `decision-constraining` / `none` |
| `δ` surprise | `better` / `as` / `worse` than the `expect` you wrote |

No prior `expect` → `δ: unscorable`. Never score surprise in hindsight.

## What the readings select

- `r advanced` + `δ as` → calibrated. Continue, with less ceremony.
- `r neutral` + `i` high → **apply** what you learned next; do not gather more.
- `r neutral` + `i none` → stall. Change approach; repeating the method is not persistence.
- `r regressed` → restore first. Never trade a regression for information.
- `δ worse` twice on one goal → the method is wrong, not the effort.

## Stakes

`imp: 1-5`, default 3. Propose it from what you already know, show what you read,
and let the user correct it; at 4-5 wait for their word. Importance does
one thing: it raises **how hard the evidence has to be to fake.**

- `imp 1-2` — any check you ran counts.
- `imp 3` — a check you did not hand-fit to.
- `imp 4-5` — an independent or held-out check, and every load-bearing fact
  verified at its source rather than recalled.

A deadline changes pace. It never lowers the evidence bar.

## Out of frame

A better idea outside the frame is a proposal, never a substitution. Say it in
one line, keep going, do not build it.

Process records stay out of the deliverable.

Reference only, not loaded: `~/.claude/skills/dopa-kernel-legacy/` holds the v0.1
routed architecture, the 18-cell frame, and the research grounding.
