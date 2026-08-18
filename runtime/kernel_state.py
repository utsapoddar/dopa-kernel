"""Derive DopaKernel routing state from a Claude Code session transcript.

The transcript is the source of truth. Nothing here mutates state or performs
side effects; every gate derives its answer by re-reading the transcript.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

SKILL_NAME = "dopa-kernel"
ADAPTERS = ("artifact.md", "decision.md", "execution.md", "combined.md")
MUTATORS = ("Write", "Edit", "NotebookEdit")

_MODULE_RE = re.compile(r"skills/dopa-kernel/modules/([a-z0-9\-]+\.md)")
_CELL_RE = re.compile(r"^[ \t>*\-]*cell\[(C|r|i)\]:[ \t]*([a-z\-]+)", re.M)
_EXPECT_RE = re.compile(r"^[ \t>*\-]*expect\[(r|i)\]:[ \t]*(\S.*)$", re.M)


@dataclass
class KernelState:
    active: bool = False
    activated_at: int | None = None
    skill_name: str | None = None
    modules_read: dict[str, int] = field(default_factory=dict)
    all_module_reads: dict[str, list[int]] = field(default_factory=dict)
    cells: list[tuple[int, str, str]] = field(default_factory=list)
    expects: list[tuple[int, str, str]] = field(default_factory=list)
    mutations: list[tuple[int, str, str]] = field(default_factory=list)
    last_user_at: int = -1
    user_turns: list[int] = field(default_factory=list)
    records: int = 0

    def domain_adapter(self) -> str | None:
        found = [(idx, name) for name, idx in self.modules_read.items() if name in ADAPTERS]
        return min(found)[1] if found else None

    def first_mutation_at(self) -> int | None:
        return self.mutations[0][0] if self.mutations else None

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
    name = block.get("name")
    if name == "Skill" and inp.get("skill") == SKILL_NAME:
        state.active = True
        if state.activated_at is None:
            state.activated_at = idx
            state.skill_name = SKILL_NAME
        return
    if name in MUTATORS:
        state.mutations.append((idx, name, str(inp.get("file_path") or "")))
    blob = str(inp.get("file_path") or inp.get("command") or "")
    match = _MODULE_RE.search(blob)
    if match:
        name = match.group(1)
        state.modules_read[name] = idx
        state.all_module_reads.setdefault(name, []).append(idx)


def _scan_text(state: KernelState, idx: int, text: str) -> None:
    for axis, value in _CELL_RE.findall(text):
        state.cells.append((idx, axis, value))
    for target, rest in _EXPECT_RE.findall(text):
        state.expects.append((idx, target, rest.strip()))
