# Domain adapter — artifact production

Invoked from the router at START when the deliverable is a text or document
whose quality is judged. Elaborates K1–K6; creates no new prohibition.

## What evidences `r` here

- The actual output line or passage for factual and textual requirements.
- A **tool measurement of the delivered text** for anything countable: length,
  item counts, section presence. A manual or remembered count is an assertion.
- Format validation for structured requirements; rendered inspection for
  presentation requirements.
- Re-measure after any edit: evidence describes the delivered state.

`r > 0` means a stated requirement moved to met-with-evidence, or a verified
deficiency was removed with nothing else made worse. `r = 0` means
requirement-relevant state is unchanged, however much was written. `r < 0`
means a previously satisfied requirement now fails, or a fact correct in an
earlier draft is now wrong.

## The loop, per unit of work

1. Pick the target with the highest expected decision impact per bounded cost.
2. In the process channel, state the prediction before acting:
   `expect[r]: ...` and, only when material, `expect[i]: ...`.
3. Draft or revise inside the envelope.
4. Verify with the evidence above; classify actual `r` and `i` separately.
5. Compare each prediction with its own target. With no prior `expect`,
   record `δ: unscorable` — never reconstruct from hindsight.
6. While verified `r` accumulates, move fast with minimal ceremony. On no
   verified progress or repeated information-only outcomes, go to
   `stall-or-replan.md`.

## Surface discipline

The finished artifact must read as if its author never saw the requirement
list: satisfy each requirement in substance, and never restate a requirement,
prohibition, or distinction as commentary inside the deliverable.
When the request names sections,
render each named section verbatim at a consistent level. Concision and
completeness are both quality dimensions; neither is bought by padding.

## Exits

- Outside-envelope alternative recognized → `proposal.md`.
- Before the final response → `completion.md`, unconditionally.
