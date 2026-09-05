# DopaKernel

DopaKernel is a semantic anti-premature-convergence controller for agent work.
It keeps the user's objective stable, allocates the next action from explicit
progress and information state, and refuses completion until every requirement
has fresh structured evidence — a verdict produced by re-running frozen
verifiers, never by the model's own account of what it did.

Behavior changes from the gap between `expect` and `got`, never from the
model's confidence that it is probably finished.

Every control rule in it is derived from a primary-literature result on how the
dopamine system actually encodes prediction error. "Dopamine-inspired" normally
means a reward scalar and a learning rate; the measured code is neither, and
taking that seriously is what produced a partial order instead of a score, a
separate regression channel instead of a signed sum, and a stakes level frozen
before the work begins. Four findings from *Nature*, *Science*, *Neuron* and
*Psychopharmacology*, each mapped to a named line of the controller — three
adopted, one deliberately rejected.

## Research grounding

**The mapping from paper to function is verifiable:** That is what makes the name honest rather than decorative.

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

**Pacing has a closed form, and adopting it would have been wrong.** Niv, Daw,
Joel & Dayan (2007, *Psychopharmacology* 191:507-520) model an agent choosing
both an action and a latency `tau`, paying a vigor cost `C_v / tau` against the
opportunity cost of time `Rbar * tau`. Their Eq. 4 gives
`tau* = sqrt(C_v / Rbar)` — optimal latency depends only on the vigor constant
and the average reward rate, identically for every action, which is why one
tonic level retunes the pace of everything at once. It is a genuinely elegant
result and it does not transfer. The derivation assumes a free-operant setting
whose scarce resource is seconds forgone from an exogenous reward stream; a
session's scarce resource is context and turns, and the task waits while the
agent thinks. So it was built, instrumented as a passive diagnostic that no
gate was allowed to read, and left in `legacy/runtime/pacing.py` rather than
promoted into the kernel.

**Three of four results survived that filter.** The fourth is documented here
precisely because rejecting it was the design decision — a result that fits the
metaphor but not the problem is the easiest kind to import by accident.

Full derivations, the policy table, and the classification frame are in
[`legacy/reference/quantities.md`](legacy/reference/quantities.md) and
[`legacy/reference/matrix.md`](legacy/reference/matrix.md).

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

366 tests cover structure, deterministic mechanism behavior, every historical
bypass case, and decision-equivalence across protocol changes:

```sh
sh kernel/tests/structure.sh                              # 52
cd kernel && python3 -m unittest discover -s tests        # 90
python3 tests/replay_equivalence.py main                  # decision equivalence
cd ../legacy && sh tests/structure.sh                     # 89
cd runtime && python3 -m unittest discover -s tests       # 135
```

`replay_equivalence.py` drives a baseline checkout and the working tree through
identical command sequences and asserts identical exit codes and identical
final controller state. It is what lets the protocol get cheaper without the
kernel's decisions moving.

## Evidence boundary and limits

The threat model is a cooperative but fallible agent that may stop early,
misread progress, or rely on stale evidence — not a deliberately malicious
process running with the user's own access.

- Host sandbox and permissions own execution authority; DopaKernel owns
  semantic requirements, action selection, evidence freshness, and the
  completion decision. Auto mode changes approval friction, not whether those
  semantic requirements have been met.
- The shell classifier fails safe by construction: unknown commands are treated
  as mutations, shell substitution is never read-only, verifier commands run
  through a read-only allowlist without `shell=True`, and controller errors
  fail closed while a goal is active. Direct tool access to `.dopa` is blocked.
  It is a conservative classifier, not a full shell interpreter.
- PreToolUse is registered for every tool name, so MCP and future mutation
  tools cannot bypass generation accounting, and an active workspace goal keeps
  the gate live in delegated transcripts that never repeated the skill
  invocation. Its authority ends at deliberate same-user modification of
  controller state, hooks, or settings, and at processes outside the installed
  hooks: this is agent control, not an operating-system sandbox.
- Candidate semantics and evidence-level labels originate in the goal contract;
  deterministic code validates and applies them. At high stakes, make verifier
  independence concrete and user-visible.
- The Claude PreToolUse hook uses the platform's `permissionDecision: "ask"`
  for cancellation and impossibility. Direct CLI invocation is an operator
  interface and assumes the caller already has user authorization.
- An earlier README reported `4/5` from a small replay. That was development
  evidence rather than an effectiveness result, and it was withdrawn.
- The standing claim is mechanical: the controller blocks the tested semantic
  premature-completion cases under this threat model. Behavioral effectiveness
  on unburned tasks is a separate question and wants its own preregistered
  evaluation.

## Version log

### Current — semantic goal controller

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

### v0.1 — routed architecture (preserved)

`legacy/` keeps the routed architecture and the 18-cell research frame. The
matrix is not redundant: its semantic dimensions remain useful. The mandatory
module-reading and self-authored paperwork around it were.
