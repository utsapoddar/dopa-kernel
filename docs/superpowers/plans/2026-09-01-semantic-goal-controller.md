# Semantic Goal Controller Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a durable semantic anti-premature-convergence controller that selects requirement-aligned work and permits completion only from fresh structured evidence.

**Architecture:** `model.py` owns goal state and receipts, `policy.py` chooses actions without collapsing progress and information, `evaluator.py` decides completion independently, and `decide.py` exposes the CLI. Existing hook filenames remain stable and delegate to those components.

**Tech Stack:** Python 3 standard library, `unittest`, Claude Code hooks, portable JSON state.

---

### Task 1: Durable goal state

**Files:**
- Create: `kernel/model.py`
- Create: `kernel/tests/test_model.py`
- Modify: `.gitignore`

- [ ] Write failing tests proving unfinished goals cannot be replaced, completed goals can be replaced, booleans require real JSON booleans, and attempts remain scoped to one goal.
- [ ] Run `cd kernel && python3 -m unittest tests.test_model -v` and confirm the missing module failure.
- [ ] Implement validated goal contracts, atomic persistence, goal IDs, mutation generations, and exact state paths.
- [ ] Re-run the focused tests and the complete lean suite.

### Task 2: Semantic action policy

**Files:**
- Create: `kernel/policy.py`
- Create: `kernel/tests/test_policy.py`

- [ ] Write failing tests for hard-envelope exclusion, regression protection, requirement priority, progress-first selection, decision-changing information, dominated research rejection, and persistent two-strike closure.
- [ ] Run the focused tests and confirm the missing policy failure.
- [ ] Implement the deterministic partial-order policy and outcome transition.
- [ ] Re-run focused and complete lean tests.

### Task 3: Structured verification and independent evaluation

**Files:**
- Create: `kernel/evaluator.py`
- Create: `kernel/tests/test_evaluator.py`
- Modify: `kernel/decide.py`

- [ ] Write failing tests for missing, failed, weak, and stale evidence; non-test file verification; regression blocking; and all-requirements-met.
- [ ] Run the focused tests and confirm they fail because the evaluator and CLI do not exist.
- [ ] Implement frozen command/file verifiers, evidence receipts, evidence-level enforcement, and `met/not_met/impossible` verdicts.
- [ ] Replace the legacy CLI with `start`, `select`, `outcome`, `verify`, `evaluate`, and `status` while keeping `select` usage recognizable.
- [ ] Re-run focused and complete lean tests.

### Task 4: Harden both hooks

**Files:**
- Modify: `kernel/gate_decide.py`
- Modify: `kernel/gate_tests.py`
- Modify: `kernel/tests/test_decide.py`
- Modify: `kernel/tests/test_gate_tests.py`

- [ ] Add failing adversarial tests for compound-command exemptions, substring paths, `touch`, Node writes, `curl -o`, stale receipts after mutation, fake test summaries, unrecognized runners, and no-test tasks.
- [ ] Run the focused tests and confirm each historical bypass fails.
- [ ] Implement exact control-command recognition, conservative mutation classification, mutation accounting, and evaluator-backed Stop decisions.
- [ ] Re-run all hook and lean tests.

### Task 5: Skill and documentation

**Files:**
- Modify: `SKILL.md`
- Modify: `README.md`
- Modify: `kernel/tests/structure.sh`
- Create: `reference/goal-contract.md`

- [ ] Change structural tests first to require goal framing, receipts, evaluator routing, fresh evidence, and compatibility entrypoints rather than an arbitrary line cap.
- [ ] Run the structural test and confirm it fails against the old skill.
- [ ] Rewrite the skill around the semantic loop and document the contract and platform `/goal` composition.
- [ ] Correct the historical evaluation wording and document current limits without claiming effectiveness.
- [ ] Run structural validation and the bundled skill validator.

### Task 6: Integration and installation verification

**Files:**
- Create: `kernel/tests/test_integration.py`
- Update: `~/.claude/skills/dopa-kernel/SKILL.md` after repository verification

- [ ] Write an integration test for start -> select -> mutate -> verify -> stale -> reverify -> met, plus a second-goal isolation test.
- [ ] Run it before the final implementation adjustments and confirm the expected failure.
- [ ] Make only the changes needed for the integration test to pass.
- [ ] Run lean, legacy, structural, adversarial, validator, and integration suites from a clean checkout.
- [ ] Copy the verified `SKILL.md` to the installed location, confirm hashes match, and confirm existing settings still reference valid hook entrypoints.
- [ ] Inspect the final diff requirement by requirement and report any remaining limitation without redefining completion.
