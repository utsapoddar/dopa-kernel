# DopaKernel

A control loop for agent work, in 79 lines and two gates.

The idea comes from dopamine as a *prediction-error* signal: not a score of how
good something is, but the gap between what you expected and what happened — and
that gap is what should change behaviour. Two things follow, and they are the
whole design.

**You do not pick the path.** Enumerate the ways you infer could reach the goal,
score each on cost, upside and confidence, say whether its failure is recoverable
and whether its uncertainty is cheaply reducible, and a program applies the rule.
**You do not decide you are finished.** If the last thing you ran failed, the
turn does not end.

## What's here

- `SKILL.md` — the kernel: the loop, the three readings (`r` progress, `i`
  information, `δ` surprise), and the `imp` stakes scale, where importance does
  exactly one thing — it raises how hard the evidence has to be to fake.
- `kernel/decide.py` — path selection and abandonment, computed rather than
  asserted.
- `kernel/gate_decide.py` — `PreToolUse`. No work until the rule has chosen. It
  **recomputes** the rule from the inputs stored in the record, so a hand-edited
  record claiming a different winner is rejected.
- `kernel/gate_tests.py` — `Stop`. Refuses to end a turn when the last test run
  failed, read from the runner's own summary rather than the shell exit code,
  because a shell that successfully runs a failing suite exits 0.
- `legacy/` — the v0.1 routed architecture, preserved. See its README.

## The selection rule

Applied in order, by `decide.py`:

1. **Unrecoverable failure is eligible only when nothing recoverable exists.**
   Upside never buys back a loss you cannot undo.
2. **Low confidence plus cheaply reducible uncertainty returns `reduce-first`**
   rather than a path — go look, then select again. If the second selection
   picks what the first would have picked anyway, that research was `i: none`
   and it says so.
3. **Otherwise, best expected value per unit cost.** This is why the cheap
   untested option usually beats the safe expensive one: when failure is
   recoverable, a cheap failure is a cheap experiment, and the safe path teaches
   you nothing. Dividing by cost stops a cost-1 lottery ticket winning on
   cheapness alone.

Abandonment is a count, not resolve: two consecutive worse-than-expected
outcomes close a path, the gate then refuses further work on it, and the next
selection must exclude it.

The agent supplies the scores — that is inference and cannot be mechanised. It
does not supply the answer.

## Why it is this small

v0.1 was 106 kernel lines, eight modules, two reference documents and four
gates. Against a matched no-controller baseline on five objectively verified
coding probes, judged by a held-out oracle suite:

| | result |
|---|---|
| baseline, no controller | **5/5** |
| v0.1, seven rules and eight modules | **2/5** |
| this kernel | **4/5** |

v0.1 did not merely fail to help; it did measurably worse than nothing, using
three to four times the turns. The cause was structural. Every one of its four
gates checked whether a file had been read or a line had been typed — artefacts
the agent authors itself. So its completion gate fired in all five treatment
sessions, including all three failures, and one session recorded
`cell[r]: advanced` on code failing three of five visible tests.

Replayed against those same traces, `gate_tests.py` fires on exactly the three
that failed and stays silent on the two that passed.

The lesson is not that rules do not work. It is that a rule nothing can check is
a suggestion, and suggestions cost context.

## Install

```
cp SKILL.md ~/.claude/skills/dopa-kernel/SKILL.md
```

Then register both gates in `~/.claude/settings.json`:

```json
"PreToolUse": [{"matcher": "Write|Edit|NotebookEdit|Bash",
  "hooks": [{"type": "command",
             "command": "python3 /path/to/dopa-kernel/kernel/gate_decide.py"}]}],
"Stop": [{"matcher": "*",
  "hooks": [{"type": "command",
             "command": "python3 /path/to/dopa-kernel/kernel/gate_tests.py"}]}]
```

Activate with `Dopa mode` in a prompt. Tests: `sh kernel/tests/structure.sh`
and `cd kernel && python3 -m unittest discover -s tests`.

## Limits, stated plainly

- **The scores are not checked.** Rate a doomed path confidence 5 and the rule
  faithfully picks it. What catches that is the outcome counter closing it after
  two failures — recovery, not prevention.
- **`gate_tests.py` only covers work that runs tests.** Writing and pure
  decision tasks have no unauthored observation to read, so there the kernel is
  advice. Adding rules would not change that.
- **4/5 still loses to 5/5.** On this evidence the kernel has gone from harmful
  to roughly break-even on coding. It has not been shown to help.
- The five probes above were scored under v0.1 and are burned: they are
  development evidence and cannot support an effectiveness claim.
