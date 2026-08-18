# DopaKernel runtime

Hooks that make the kernel's routing rules mechanically enforced rather than
advisory. The session transcript is the source of truth; every gate re-derives
its answer by parsing it.

| Module | Role |
|---|---|
| `kernel_state.py` | Parse a transcript into activation, module reads, and emitted cell/expect lines |
| `dictionary.py` | The 18-cell frame: legality, Pareto partial order, regression floor |
| `bash_effect.py` | Classifies a shell command as read_only / writing / destructive |
| `pacing.py` | `Rbar` and `tau* = sqrt(C_v/Rbar)` (Niv et al. 2007, Eq. 4) |
| `gate_pretooluse.py` | Blocks mutations and destructive shell missing adapter / rollback / proposal |
| `gate_stop.py` | Blocks turn-end missing the completion walk, on turns that did work |
| `compliance.py` | Passive scan of existing transcripts: how often each routing rule was followed, over opportunities only |

Guarantees: inert unless the transcript shows `Skill(dopa-kernel)`; fails open
on any error; the Stop gate blocks at most twice per turn.

Run the tests: `python3 -m unittest discover -s runtime/tests`

## Passive compliance instrumentation

    python3 runtime/compliance.py            # human-readable
    python3 runtime/compliance.py --json     # machine-readable

Scans `~/.claude/projects` (or given directories) for sessions that invoked the
kernel and reports per-gate compliance. Denominators count **opportunities**, so
a rule that never had a chance to apply is reported `n/a` rather than as a pass.
No probes are consumed; the report records counts, rates, and session ids only,
never message content.

Coverage limits are printed with every report and should be read alongside the
rates: Bash-mediated state changes are not counted as mutations, an undeclared
envelope excursion is invisible, and every turn-end counts as a completion
opportunity.
