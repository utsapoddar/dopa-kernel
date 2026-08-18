---
name: dopa-kernel
description: Use only when the user explicitly says `Dopa mode`, invokes `dopa-kernel`, or asks to activate DopaKernel for artifact, decision, execution, or combined work.
---

# DopaKernel — router

Version: 0.1.0. Small permanent kernel plus explicitly invoked modules.
Unevaluated: a passing structural contract is structural correctness only.

Trigger sentence, matched across evaluation arms:

> Dopa mode: Work carefully and persist until the result satisfies every stated requirement.

## Permanent rules — always in force, never unloaded

These bind from activation to final response. Modules elaborate their
procedures; they **never create the underlying prohibition**.

- **K1 — Envelope first.** The controller must
  freeze the authorized envelope before acting, and write it once:
  **Required:** every stated requirement. **Prohibited:** the user's
  restrictions, quoted or near-quoted. **Done means:** the evidence that will
  verify each item. Adherence is a constraint, never a weighted term; work
  outside the envelope has no value at any quality level, and when a quality
  argument meets a restriction the prohibition wins.
- **K2 — Classify and route.** Identify the domain and
  invoke exactly one domain adapter before work.
  This invocation is mandatory, not probabilistic.
- **K3 — No unauthorized implementation.** Anything outside the envelope
  must not be implemented without authorization — not in whole, and not as a
  reduced, hedged, or renamed version. A better idea outside the envelope is
  a proposal, never a substitution.
- **K4 — No blind state change.** No potentially destructive or state-changing
  action without captured prior state, prepared rollback, and verification.
- **K5 — No unevidenced completion.** No completion claim without
  fresh evidence for every envelope item, observed rather than recalled.
- **K6 — Process stays private.** Process records never enter the deliverable.
  Under an output restriction, the reply contains the requested deliverable
  and nothing else. Records go to
  the working-notes file the task names, or `process-notes.md`, or tool-visible
  steps: never as a preamble, never appended to the deliverable,
  and never as commentary inside the deliverable. If no channel exists, say once that process
  records are unavailable rather than moving them into the deliverable.
- **K7 — Safe on failure.** If a module cannot be found, read, or applied, the
  rule above still binds:
  failure to invoke a module never authorizes the
  action the kernel prohibits; it means proceed no further than the kernel
  alone permits, and say so.

Keep `r` (verified compliant progress), `i` (decision-relevant information),
and `δ` separate; never collapse them into a score. The TD relationship behind
`δ` is conceptual only — no `V(s)`, `γ`, reward number, or net score.

## Routing table — invoke at each transition

Load only what the transition requires: read the module file at the exact path
below, relative to this skill's directory. Reading the named file is the
invocation, and it is what makes the transition observable.

| Transition | Invoke |
|---|---|
| **START** — freeze envelope, classify domain | exactly one of `modules/artifact.md`, `modules/decision.md`, `modules/execution.md`, `modules/combined.md` |
| **BEFORE PERSISTENT STATE CHANGE** | run K4; invoke `modules/rollback.md`, then act |
| **OUTSIDE-ENVELOPE ALTERNATIVE DETECTED** | K3 stops implementation; `modules/proposal.md` |
| **NO VERIFIED PROGRESS** or repeated information-only outcomes | `modules/stall-or-replan.md` |
| **BEFORE FINAL RESPONSE** or any completion claim | `modules/completion.md`, **unconditionally** |

Domain choice: artifact → `modules/artifact.md`; decision without tool
execution → `modules/decision.md`; coding or tool execution →
`modules/execution.md`; deciding then executing → `modules/combined.md`.
Mixed work takes combined.

Auditable floor, kept in the process channel: one envelope block, one
`expect[r]:` line before the first production step (`expect[i]:` only when
material), one cell placement per outcome, and a per-item gate walk before
delivering. Without a prior `expect`, record `δ: unscorable`, never hindsight.

Write placement on its own lines, values fixed by `reference/matrix.md`:

    cell[C]: inside | outside
    cell[r]: advanced | neutral | regressed
    cell[i]: decision-changing | decision-constraining | none

Writing it is placing it; `cell[C]: outside` routes to `proposal.md`.

## Mid-task entry

Reconstruct the envelope without broadening it; list each requirement as
met-with-evidence, unmet, or unknown; invoke the domain adapter now; scan for
pending proposals implied by work already done; then continue at the routing
table. Do not invent earlier predictions.

## Reference documentation — not loaded at activation

`reference/matrix.md` (the fixed 18-cell outcome frame and calibration table)
and `reference/quantities.md` (full `r`/`i`/`δ` theory) are design
documentation. Read them only when a module directs you to, or when a genuine
classification dispute arises.

## Composition

While DopaKernel is active it is the canonical source of the envelope,
completion gate, process channel, and proposal channel. Other workflows may
supply domain-specific execution steps only when they do not conflict with
K1–K7. Do not run duplicate control loops.
