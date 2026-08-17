# DopaKernel

**An intent-gated motivational control kernel for AI agents.**

DOPA stands for **Directive-Oriented Persistence Architecture**. DopaKernel
keeps an agent working toward the user's authorized objective until the result
is evidenced, while preventing perceived quality improvements from silently
overriding instructions.

## Why

Agentic systems can stop when work is merely plausible, continue without
making progress, or substitute an unsolicited "better" objective. DopaKernel
adds a compact control layer that separates:

- **Adherence:** the authorized envelope is a hard gate, not a weighted score.
- **Progress (`r`):** verified movement toward that envelope.
- **Information (`i`):** observations that change the next decision.
- **Calibration (`delta`):** whether an outcome matched its prospective prediction.
- **Completion:** every requirement is evidenced and no worthwhile authorized improvement remains.

## Architecture

```text
Explicit activation
       |
       v
Permanent kernel: envelope + authorization + evidence gates
       |
       +--> one domain adapter
       |      artifact | decision | execution | combined
       |
       +--> conditional modules
       |      proposal | rollback | stall/replan
       |
       `--> unconditional completion check
```

The permanent kernel retains every safety-critical prohibition. Modules add
procedural detail; failure to load one never grants permission to cross the
user's envelope.

## Install

### Claude Code

```bash
git clone https://github.com/utsapoddar/dopa-kernel.git ~/.claude/skills/dopa-kernel
```

### Codex

```bash
git clone https://github.com/utsapoddar/dopa-kernel.git ~/.agents/skills/dopa-kernel
```

## Use

Activate it explicitly:

```text
Dopa mode: Work carefully and persist until the result satisfies every stated requirement.
```

The router classifies the task as one of four domains:

| Domain | Use |
|---|---|
| Artifact | Text, documents, or other judged deliverables |
| Decision | Choosing without executing tools or changing state |
| Execution | Coding, commands, or other state-changing work |
| Combined | Making a decision and then executing it |

Process records use a task-provided working-notes file, `process-notes.md`, or
tool-visible working steps. They do not belong in the requested deliverable.

## Core invariants

1. Freeze the authorized envelope before acting.
2. Invoke exactly one domain adapter.
3. Never implement an outside-envelope alternative without authorization.
4. Protect state-changing work with prior state, rollback, and verification.
5. Never claim completion without fresh evidence for every requirement.
6. Keep process records outside the deliverable.
7. Fail closed when a module cannot be applied.

## Repository layout

```text
SKILL.md                 permanent router and invariants
modules/                 domain and transition procedures
reference/               full quantity and matrix definitions
tests/structure.sh       portable structural contract
```

## Verification

```bash
sh tests/structure.sh
```

## Evidence status

DopaKernel is experimental. Its structural contract verifies the presence and
composition of the specified mechanisms; structural correctness does not prove
mechanism execution or improved task outcomes. Behavioral effectiveness remains
to be established with controlled evaluations.
