# DopaKernel runtime

Hooks that make the kernel's routing rules mechanically enforced rather than
advisory. The session transcript is the source of truth; every gate re-derives
its answer by parsing it.

| Module | Role |
|---|---|
| `kernel_state.py` | Parse a transcript into activation, module reads, and emitted cell/expect lines |
| `dictionary.py` | The 18-cell frame: legality, Pareto partial order, regression floor |
| `pacing.py` | `Rbar` and `tau* = sqrt(C_v/Rbar)` (Niv et al. 2007, Eq. 4) |
| `gate_pretooluse.py` | Blocks mutations missing adapter / rollback / proposal |
| `gate_stop.py` | Blocks turn-end missing the completion walk |

Guarantees: inert unless the transcript shows `Skill(dopa-kernel)`; fails open
on any error; the Stop gate blocks at most twice per turn.

Run the tests: `python3 -m unittest discover -s runtime/tests`
