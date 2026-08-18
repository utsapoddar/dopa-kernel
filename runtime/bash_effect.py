"""Classify what a shell command does to persistent state.

Three defects traced to the same blind spot: mutations, the rollback gate, and
cell-placement detection all ignored Bash. Shell is arbitrary, so this is a
heuristic — but it is a conservative one, and every gate that consumes it fails
open rather than blocking on an unrecognised command.

    read_only    observes only
    writing      creates or modifies, recoverably
    destructive  removes, overwrites, or publishes; K4 wants a rollback first
"""
from __future__ import annotations

import re

_ORDER = {"read_only": 0, "writing": 1, "destructive": 2}

# Destructive: irreversible locally, or publishes outside the machine.
_DESTRUCTIVE = (
    r"\brm\b",
    r"\bgit\s+push\b",
    r"\bgit\s+reset\s+--hard\b",
    r"\bgit\s+rebase\b",
    r"\bgit\s+filter-repo\b",
    r"\bgit\s+branch\s+-D\b",
    r"\bgit\s+clean\b",
    r"\bgit\s+stash\s+drop\b",
    r"\bmv\b",
    r"\bdd\b",
    r"\bshred\b",
    r"\btruncate\b",
    r"\bgh\s+api\s+(-X|--method)\s*(POST|PUT|PATCH|DELETE)\b",
    r"\bgh\s+repo\s+(delete|edit|rename)\b",
    r"\bgh\s+(pr|release|secret)\s+(create|merge|delete|set)\b",
    r"\bcurl\b[^|]*\s(-X|--request)\s*(POST|PUT|PATCH|DELETE)\b",
    r"\bkill(all)?\b",
    r"\blaunchctl\s+(load|unload|bootout)\b",
    r"\bdefaults\s+write\b",
)

# Writing: creates or modifies, but recoverable.
_WRITING = (
    r"\btouch\b",
    r"\bmkdir\b",
    r"\bcp\b",
    r"\bln\b",
    r"\bsed\s+-i\b",
    r"\btee\b",
    r"\bchmod\b",
    r"\bchown\b",
    r"\bgit\s+(add|commit|tag|checkout|switch|merge|cherry-pick|revert|stash)\b",
    r"\b(npm|pnpm|yarn|pip|pip3|brew|cargo|go)\s+(install|add|remove|uninstall)\b",
)

# A redirect that writes a file. Excludes /dev/null and fd duplication (2>&1).
_REDIRECT = re.compile(r"(?<![0-9&])>{1,2}\s*(?!&)(?!/dev/null)(?!/dev/stderr)\S+")


def classify(command: str | None) -> str:
    if not command:
        return "read_only"
    text = str(command)
    effect = "read_only"
    for pattern in _WRITING:
        if re.search(pattern, text):
            effect = "writing"
            break
    if effect == "read_only" and _REDIRECT.search(text):
        effect = "writing"
    for pattern in _DESTRUCTIVE:
        if re.search(pattern, text):
            return "destructive"
    return effect


def is_state_changing(command: str | None) -> bool:
    return _ORDER[classify(command)] > 0


def is_destructive(command: str | None) -> bool:
    return classify(command) == "destructive"
