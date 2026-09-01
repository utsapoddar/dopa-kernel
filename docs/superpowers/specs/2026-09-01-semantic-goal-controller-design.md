# Semantic Goal Controller Design

## Objective

DopaKernel prevents premature convergence by keeping the authorized objective
stable, allocating the next unit of work from semantic task state, and refusing
completion until fresh evidence proves every requirement.

The design preserves the existing `C / r / i / δ / imp` model and explicit
`Dopa mode` activation. It replaces the current self-reported path state and
test-output parser with a durable goal contract, deterministic action policy,
structured evidence receipts, and an independent completion evaluator.

## Non-goals

- Do not restore the legacy eight-module routing ceremony.
- Do not require an external model API.
- Do not replace Codex or Claude `/goal`; DopaKernel is the semantic policy and
  evidence layer beneath either platform's continuation mechanism.
- Do not claim behavioral effectiveness from structural or unit tests.

## Goal contract

One `.dopa/goal.json` record is authoritative for the current workspace. It is
created from a user-visible JSON contract containing:

- objective and immutable goal ID;
- explicit requirements and hard constraints;
- importance `imp` and the evidence level it requires;
- an exact verifier for each requirement;
- current mutation generation;
- selected action, attempts, closed paths, observations, and status.

Starting a different objective replaces completed state but never silently
overwrites an unfinished goal. State is goal-scoped, so attempts and closed
paths cannot contaminate later goals.

## Semantic action policy

Every candidate identifies the unmet requirement it serves and declares:

- envelope membership `C`;
- expected progress `r`;
- expected information `i`;
- prediction confidence and bounded cost;
- reversibility;
- whether uncertainty is cheaply reducible and decision-critical.

The policy applies hard eligibility before value. Outside-envelope and unsafe
regressing actions are ineligible. It prioritizes the highest-importance unmet
requirement, prefers verified-progress actions, and uses information gathering
only when the uncertainty is decision-critical and could change the selected
action. It never collapses `r` and `i` into one reward number.

Outcomes append to persistent history. Two genuinely consecutive
worse-than-expected outcomes close a path; reselection does not erase them.

## Evidence and completion

Verifier definitions are frozen in the goal contract. `decide.py verify` runs
the declared verifier rather than accepting arbitrary claimed output. Initial
support covers exact command checks and deterministic file checks.

Each receipt records the requirement, verifier identity, result, output digest,
timestamp, and mutation generation. Any later production mutation makes older
receipts stale. Evidence levels are `observed`, `independent`, and `held-out`;
the evaluator maps `imp` to the minimum accepted level.

The evaluator is independent from the worker's prose. It returns:

- `met` only when every requirement has fresh passing evidence, no known
  regression exists, and the evidence bar is met;
- `not_met` with the highest-value missing or stale requirement;
- `impossible` only when the goal record contains an externally established
  terminal blocker.

Information alone never completes a requirement.

## Hooks and continuation

`gate_decide.py` remains the PreToolUse entrypoint. It uses a conservative
command classifier: recognized read-only and verifier operations are safe;
unknown shell commands are treated as mutations. Exemptions apply only to the
exact control command, never substring matches in compound commands.

`gate_tests.py` remains the Stop entrypoint for installation compatibility. It
does not parse transcript test summaries. It runs the completion evaluator over
the durable record and blocks with the next unmet requirement and selected
action. Claude's Stop-hook loop or Codex `/goal` can then start the next turn.

## Verification

Verification requires:

- red-green unit tests for goal isolation, policy, receipts, evaluator, and
  adversarial shell classification;
- an integration test covering start -> select -> mutate -> verify -> stale ->
  reverify -> met;
- existing legacy tests remain green;
- the installed skill matches the repository and existing hook paths remain
  valid;
- README claims distinguish structural correctness from behavioral evidence.

