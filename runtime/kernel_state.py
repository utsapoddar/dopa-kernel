"""Derive DopaKernel routing state from a Claude Code session transcript.

The transcript is the source of truth. Nothing here mutates state or performs
side effects; every gate derives its answer by re-reading the transcript.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

import bash_effect

SKILL_NAME = "dopa-kernel"
ADAPTERS = ("artifact.md", "decision.md", "execution.md", "combined.md")
MUTATORS = ("Write", "Edit", "NotebookEdit")

_MODULE_RE = re.compile(r"skills/dopa-kernel/modules/([a-z0-9\-]+\.md)")
_CELL_RE = re.compile(r"^[ \t>*\-]*cell\[(C|r|i)\]:[ \t]*([a-z\-]+)", re.M)
_EXPECT_RE = re.compile(r"^[ \t>*\-]*expect\[(r|i)\]:[ \t]*(\S.*)$", re.M)
# The trailing `(?![^\n]*\|)` refuses any line that still carries a `|`, so the
# menu lines in SKILL.md (`imp: 1 | 2 | 3 | 4 | 5`) can never be misread as a
# declaration if the kernel text is ever echoed into a tool input.
_IMP_RE = re.compile(r"^[ \t>*\-]*imp:[ \t]*([1-5])\b(?![^\n]*\|)", re.M)
_DUE_RE = re.compile(r"^[ \t>*\-]*due:[ \t]*(\d{4}-\d{2}-\d{2}|none)\b(?![^\n]*\|)", re.M)
STAKES_MARKERS = ("cell[", "imp:", "due:")
DEFAULT_IMP = 3


@dataclass
class KernelState:
    active: bool = False
    activated_at: int | None = None
    skill_name: str | None = None
    modules_read: dict[str, int] = field(default_factory=dict)
    all_module_reads: dict[str, list[int]] = field(default_factory=dict)
    cells: list[tuple[int, str, str]] = field(default_factory=list)
    expects: list[tuple[int, str, str]] = field(default_factory=list)
    imps: list[tuple[int, int]] = field(default_factory=list)
    dues: list[tuple[int, str]] = field(default_factory=list)
    mutations: list[tuple[int, str, str]] = field(default_factory=list)
    bash_ops: list[tuple[int, str]] = field(default_factory=list)
    substantive_ops: list[int] = field(default_factory=list)
    last_user_at: int = -1
    user_turns: list[int] = field(default_factory=list)
    records: int = 0

    def domain_adapter(self) -> str | None:
        found = [(idx, name) for name, idx in self.modules_read.items() if name in ADAPTERS]
        return min(found)[1] if found else None

    def first_mutation_at(self) -> int | None:
        return self.mutations[0][0] if self.mutations else None

    def substantive_since(self, index: int) -> bool:
        """Did any non-bookkeeping tool call happen at or after `index`?"""
        return any(i >= index for i in self.substantive_ops)

    def first_destructive_at(self) -> int | None:
        for idx, effect in self.bash_ops:
            if effect == "destructive":
                return idx
        return None

    def importance(self) -> int:
        """Declared `imp`, or the kernel's documented default when none was set.

        Callers that must distinguish "declared 3" from "never declared" ask
        importance_declared_at() instead; a stake nobody set is not a stake.
        """
        return self.imps[-1][1] if self.imps else DEFAULT_IMP

    def importance_declared_at(self) -> int | None:
        return self.imps[0][0] if self.imps else None

    def due(self) -> str | None:
        return self.dues[-1][1] if self.dues else None

    def latest_envelope_class(self) -> str | None:
        for _idx, axis, value in reversed(self.cells):
            if axis == "C":
                return value
        return None


def parse(path: str) -> KernelState:
    state = KernelState()
    try:
        raw = Path(path).read_text(errors="replace")
    except OSError:
        return state
    for idx, line in enumerate(raw.splitlines()):
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except ValueError:
            continue
        state.records += 1
        message = record.get("message") or {}
        role = message.get("role")
        content = message.get("content")
        # Hook feedback is injected as a user-role record but flagged isMeta.
        # Counting it as a turn would let a Stop block inflate the very
        # denominator the gate is measured against, and would make a prior
        # completion read look stale to gate_stop.decide().
        if role == "user" and isinstance(content, str) and not record.get("isMeta"):
            state.last_user_at = idx
            state.user_turns.append(idx)
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict):
                continue
            kind = block.get("type")
            if kind == "tool_use":
                _scan_tool_use(state, idx, block)
            elif kind == "text" and role == "assistant":
                _scan_text(state, idx, block.get("text") or "")
    return state


def _scan_tool_use(state: KernelState, idx: int, block: dict) -> None:
    inp = block.get("input") or {}
    tool = block.get("name")

    if tool == "Skill" and inp.get("skill") == SKILL_NAME:
        state.active = True
        if state.activated_at is None:
            state.activated_at = idx
            state.skill_name = SKILL_NAME
        return

    if tool in MUTATORS:
        state.mutations.append((idx, tool, str(inp.get("file_path") or "")))

    effect = bash_effect.classify(inp.get("command")) if tool == "Bash" else None
    if effect and effect != "read_only":
        state.bash_ops.append((idx, effect))

    # K6 sends process records to a notes file rather than the reply, so a cell
    # placement usually arrives as written content, not as assistant text.
    # Scanning only text would make correct behaviour invisible to the gates.
    for field_name in ("content", "new_string", "command"):
        written = inp.get(field_name)
        if isinstance(written, str) and any(m in written for m in STAKES_MARKERS):
            _scan_text(state, idx, written)

    blob = str(inp.get("file_path") or inp.get("command") or "")
    match = _MODULE_RE.search(blob)
    if match:
        module = match.group(1)
        state.modules_read[module] = idx
        state.all_module_reads.setdefault(module, []).append(idx)

    # Routing (invoking the skill, reading its modules) is bookkeeping, not work.
    # A turn that only routes has nothing to verify, so it must not be gated.
    bookkeeping = bool(match) and effect in (None, "read_only")
    if not bookkeeping:
        state.substantive_ops.append(idx)


def _scan_text(state: KernelState, idx: int, text: str) -> None:
    for axis, value in _CELL_RE.findall(text):
        state.cells.append((idx, axis, value))
    for target, rest in _EXPECT_RE.findall(text):
        state.expects.append((idx, target, rest.strip()))
    for value in _IMP_RE.findall(text):
        state.imps.append((idx, int(value)))
    for value in _DUE_RE.findall(text):
        state.dues.append((idx, value))
