# DopaKernel

DopaKernel is a semantic anti-premature-convergence controller for agent work.
It keeps the user's objective stable, allocates the next action from explicit
progress and information state, and refuses completion until every requirement
has fresh structured evidence.

Its threat model is a cooperative but fallible agent that may stop early,
misread progress, or rely on stale evidence. It is not a security boundary
against a deliberately malicious process running with the user's own access.

The name comes from dopamine as prediction error: behavior should change from
the gap between `expect` and `got`, not from the model's confidence that it is
probably finished.

## Research grounding

The controller's odder-looking commitments — no single score, regressions in
their own channel, importance fixed before the work starts — are not style
preferences. Each was adopted from a specific finding about how the dopamine
system actually encodes prediction error.

**Never sum `r` and `i`.** Dabney et al. (2020, *Nature* 577:671-675) recorded
40 VTA cells across 6 animals and found dopamine encodes reward prediction
error *distributionally*: each cell carries its own asymmetric scaling for
positive versus negative RPE, mean ratio 0.48, with significant diversity
(`F(38,234) = 2.93`, `p = 4e-7`). For one identical 5 uL reward, 13/40 cells
fired above baseline while 10/40 fired below — same reward, opposite sign,
simultaneously. A scalar would discard exactly the structure the separate axes
preserve, so no exchange rate between progress and information exists and none
may be invented. Live in `policy.choose`, which is a partial order rather than
a score.

**A regression is not negative progress.** Bayer & Glimcher (2005, *Neuron*
47:129-141) found firing rate encodes positive RPE but does not carry the
negative magnitude; Bayer, Lau & Glimcher (2007) located that magnitude in the
duration of the post-reward interspike pause instead. Two encodings, two units,
no signed scalar — which is why a regression gets its own channel and is never
netted against progress. Live as `known_regression`, which forces restoration
before other work proceeds.

**Stakes are set at the cue, not the outcome.** Tobler, Fiorillo & Schultz
(2005, *Science* 307:1642-1645) found dopamine neurons do not encode absolute
reward magnitude: responses shift relative to expected value and the gain
adapts to the variance of reward value, so an identical reward produces a
different response under a different stakes context. Critically the adaptation
is driven by reward-predicting stimuli — the scale is set before the outcome
arrives. That is why `imp` is declared with the goal contract, frozen into the
goal identity at `start`, and floors the evidence bar afterwards; it is never
inferred once results are in.

**Pacing has a closed form — and it was cut.** Niv, Daw, Joel & Dayan (2007,
*Psychopharmacology* 191:507-520) model an agent choosing both an action and a
latency `tau`, paying a vigor cost `C_v / tau` against the opportunity cost of
time `Rbar * tau`. Their Eq. 4 gives `tau* = sqrt(C_v / Rbar)`: optimal latency
depends only on the vigor constant and the average reward rate, identically for
every action, which is why one tonic level retunes the pace of everything at
once. This is **not** part of the current kernel. It governed pace and never
quality, no gate ever read it, and its derivation assumes a free-operant
setting whose scarce resource is seconds rather than context and turns. It
survives as `legacy/runtime/pacing.py` and is documented for the record, not
for use.

Full derivations, the policy table, and the classification frame are in
[`legacy/reference/quantities.md`](legacy/reference/quantities.md) and
[`legacy/reference/matrix.md`](legacy/reference/matrix.md). They sit under
`legacy/` because the routed architecture around them was retired, not because
the findings were — three of the four commitments above are load-bearing in
`kernel/` today.

These results justify the controller's design commitments. They say nothing
about whether DopaKernel improves agent success rates; see the evidence
boundary below.

## What changed

The original lean kernel had two sound ideas: do not let prose choose the path,
and do not let a failing observation become victory. Its implementation was too
narrow: it remembered one selection, parsed the last recognizable test summary,
and allowed several shell and path exemptions. Semantic fields (`C`, `r`, `i`,
`δ`, `imp`) did not control runtime decisions.

The current controller connects those ideas end to end:

- `kernel/model.py` — validated, goal-scoped `.dopa/goal.json`, frozen
  requirements, atomic state, mutation generations, attempts, and closed paths.
- `kernel/policy.py` — deterministic action selection with hard envelope and
  regression constraints, requirement priority, progress-first behavior, and
  decision-critical `reduce-first` research.
- `kernel/evaluator.py` — shell-free command/file verifiers, mutation detection,
  live final re-verification, evidence receipts, and independent
  `met / not_met / impossible` completion decisions.
- `kernel/decide.py` — `start`, `select`, `outcome`, `verify`, `block`, `cancel`,
  `evaluate`, and `status` CLI. Machine-readable output is compact, and `status`
  shows the last `SWITCH_AFTER` attempts plus a recorded count rather than the
  whole history — that window is all path closure consults, so the display cost
  stays flat as a session grows. `.dopa/goal.json` still records every attempt.
- `kernel/gate_decide.py` — Claude PreToolUse gate. Exact control commands are
  exempt; unknown shell commands are mutations; authorization is locked and
  later mutations stale earlier evidence.
- `kernel/gate_tests.py` — compatibility-named Claude Stop gate. It reads the
  evaluator, never transcript test-like prose.
- `legacy/` — preserved v0.1 routed architecture and 18-cell research frame.

The matrix is not redundant: its semantic dimensions remain useful. The
mandatory module-reading and self-authored paperwork around it were redundant.

## Minimal workflow

Use absolute paths to the controller while keeping the target workspace as cwd:

```sh
python3 /path/to/dopa-kernel/kernel/decide.py start /tmp/dopa-goal.json
python3 /path/to/dopa-kernel/kernel/decide.py select /tmp/dopa-candidates.json
# make one authorized mutation, observe it
python3 /path/to/dopa-kernel/kernel/decide.py outcome /tmp/dopa-outcome.json
python3 /path/to/dopa-kernel/kernel/decide.py verify requirement-id
python3 /path/to/dopa-kernel/kernel/decide.py evaluate
```

If the user explicitly changes the objective, run
`decide.py cancel /tmp/dopa-cancel.json` before starting its replacement. See
the contract guide for the authorized cancellation and evidence-backed blocker
schemas. With the Claude hooks installed, both `cancel` and `block` force a
native permission prompt, including in auto mode.

See [`reference/goal-contract.md`](reference/goal-contract.md) for both schemas
and the exact evidence semantics.

## How this composes with `/goal`

`/goal` and DopaKernel solve different layers of the same failure mode:

| Layer | Responsibility |
|---|---|
| Codex `/goal` | Thread-persistent objective, continuation turns, a requirement-by-requirement completion-audit prompt, usage accounting, and user lifecycle controls |
| Claude `/goal` | Session goal restored on resume, driven by a prompt-based Stop hook whose separate small model reads the conversation and returns not-yet/met/impossible |
| DopaKernel | Requirement decomposition, semantic action allocation, path closure, frozen verification, and fresh-evidence completion |

For Codex, keep the platform goal and Dopa objective identical; Codex supplies
continuation while Dopa supplies policy and evidence. For Claude, install the
Dopa hooks so the Stop decision uses structured receipts rather than inferred
test summaries. DopaKernel does not call a second external model API.

The lesson is **not** to duplicate platform loop machinery. Codex already tells
the worker not to shrink the objective and to audit every requirement before
calling its completion tool. Claude already uses a fresh model rather than the
worker for the terminal decision, but that evaluator cannot run tools and only
sees what the worker surfaced. DopaKernel fills the remaining gap:
deterministic semantic selection plus verifier receipts tied to post-mutation
state.

Current primary references:

- [Codex Goal mode release](https://learn.chatgpt.com/docs/changelog) and
  [v0.147.0 continuation contract](https://github.com/openai/codex/blob/rust-v0.147.0/codex-rs/ext/goal/templates/goals/continuation.md)
- [Codex v0.147.0 goal tool contract](https://github.com/openai/codex/blob/rust-v0.147.0/codex-rs/ext/goal/src/spec.rs)
- [Claude Code `/goal` documentation](https://code.claude.com/docs/en/goal)

## Install for Claude Code

Keep one source of truth. Clone or place this repository at a stable path, then
link its loader adapter. Do not link the repository root: recursive skill
discovery may otherwise expose `legacy/SKILL.md` as a duplicate active skill.

```sh
ln -s /absolute/path/to/dopa-kernel/adapters/claude ~/.claude/skills/dopa-kernel
```

The adapter routes the agent to the canonical root `SKILL.md`; it contains no
independent behavioral copy.

Register the stable absolute hook paths in `~/.claude/settings.json`:

```json
{
  "hooks": {
    "PreToolUse": [{
      "matcher": "*",
      "hooks": [{"type": "command", "command": "python3 /absolute/path/to/dopa-kernel/kernel/gate_decide.py"}]
    }],
    "Stop": [{
      "matcher": "*",
      "hooks": [{"type": "command", "command": "python3 /absolute/path/to/dopa-kernel/kernel/gate_tests.py"}]
    }]
  }
}
```

Activate only with `Dopa mode` or explicit `dopa-kernel` invocation.

## Verification

```sh
sh kernel/tests/structure.sh
cd kernel && python3 -m unittest discover -s tests -v
cd ../legacy && sh tests/structure.sh
cd runtime && python3 -m unittest discover -s tests -v
```

These tests establish structural and deterministic mechanism behavior, including
the historical bypass cases. They do **not** establish that DopaKernel improves
real-world agent success rates.

## Evidence boundary and limits

- Host sandbox and permissions own execution authority; DopaKernel owns
  semantic requirements, action selection, evidence freshness, and the
  completion decision. Auto mode changes approval friction, not whether those
  semantic requirements have been met.
- Candidate semantics and evidence-level labels originate in the goal contract;
  deterministic code validates and applies them but cannot prove the judgments
  were wise. At high stakes, make independence concrete and user-visible.
- The shell classifier is conservative, not a full shell interpreter. Unknown
  commands are treated as mutations, shell substitution is never read-only,
  verifier commands use a read-only allowlist without `shell=True`, and active
  controller errors fail closed. Direct tool access to `.dopa` is blocked.
- PreToolUse is registered for every tool name so MCP and future mutation tools
  cannot bypass generation accounting. An active workspace goal also keeps the
  gate active in delegated transcripts that lack the original skill invocation.
  This is still an agent-control mechanism, not an operating-system security
  sandbox. Deliberate same-user modification of controller state, hooks, or
  settings, and processes outside the installed hooks, remain outside its
  authority.
- The Claude PreToolUse hook uses the platform's `permissionDecision: "ask"`
  for cancellation and impossibility. Direct CLI invocation is an operator
  interface and therefore assumes the caller already has user authorization.
- A previous README reported `4/5` from a small replay. That was development
  evidence, not a valid effectiveness result, and is not retained as a claim.
- The current public claim is mechanical only: the controller blocks the tested
  semantic premature-completion cases under this threat model. Behavioral
  effectiveness still requires a fresh, preregistered evaluation on unburned
  tasks.
