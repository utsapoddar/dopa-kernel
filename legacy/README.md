# legacy — the v0.1 routed architecture (reference only)

Preserved verbatim, not loaded by the kernel. Superseded 2026-08-20.

`SKILL.md` (106 lines), eight `modules/` (~420 lines), `reference/matrix.md`
and `reference/quantities.md`, the four-gate `runtime/`, and its 89 structural
plus 135 runtime tests.

**Why it was replaced.** The 2026-08-19 four-track sweep ran it against a
matched no-controller baseline on five objectively verified coding probes.
Baseline passed 5/5. The controller passed 2/5, using 18-29 turns against
baseline's 6-8. `completion.md` was invoked in all five treatment sessions,
including all three failures, and one session recorded `cell[r]: advanced` on
code failing three of five visible tests.

The cause is structural: every gate in this design checked whether a file had
been read or a line had been typed. None read an observation the agent could
not author, so the whole apparatus verified paperwork rather than results.

The research grounding lives in `reference/quantities.md` and
`reference/matrix.md` and is still the basis of the current kernel — the
prediction/observation/error loop, the separation of `r` and `i`, the
regression floor, and importance rescaling the evidence bar. What was cut is
the bookkeeping built on top of it.

Evaluation evidence: `~/.claude/evaluations/dopa-kernel/2026-08-19-v2/`.
