# DopaKernel

A control loop for agent work, in 66 lines. Frame, predict, act, observe,
compare, and refuse to claim done against a failing observation.

The idea is from the neuroscience of dopamine as a *prediction-error* signal —
not a score of how good something is, but a measure of the gap between what you
expected and what happened, and that gap is what should change behaviour.

## What's here

- `SKILL.md` — the kernel. The whole loop and the three readings (`r`, `i`, `δ`)
  plus the `imp` stakes scale.
- `kernel/gate_tests.py` — the enforcement, and there is exactly one: a `Stop`
  hook that refuses to end a turn when the last test run in the transcript
  failed. It reads the runner's own summary, not the shell exit code, because a
  shell that successfully runs a failing suite exits 0.
- `legacy/` — the v0.1 routed architecture, kept for reference. See its README.

## Why it is this small

v0.1 was 106 kernel lines, eight modules, two reference documents, and four
gates. Measured against a matched no-controller baseline on five objectively
verified coding probes, **baseline passed 5/5 and the controller passed 2/5**,
using three to four times the turns.

Every one of those four gates checked whether a file had been read or a line
had been typed — things the agent writes itself. So the completion gate fired in
all five treatment sessions, including all three failures, and one session
recorded `cell[r]: advanced` on code failing three of five visible tests.

The single gate here fires on exactly those three failing sessions and stays
silent on the two that passed, replayed against the real traces.

The lesson is not that rules do not work. It is that a rule nothing can check
is a suggestion, and suggestions cost context.

## Install

Copy `SKILL.md` to `~/.claude/skills/dopa-kernel/SKILL.md`, then register the
gate as a `Stop` hook in `~/.claude/settings.json`:

```json
{"matcher": "*", "hooks": [{"type": "command",
  "command": "python3 /path/to/dopa-kernel/kernel/gate_tests.py"}]}
```

Activate with `Dopa mode` in a prompt.
