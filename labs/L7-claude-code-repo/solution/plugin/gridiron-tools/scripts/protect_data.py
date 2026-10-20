#!/usr/bin/env python3
"""PreToolUse hook: block changes to the read-only fixtures in data/.

Claude Code runs this before Write, Edit, NotebookEdit and Bash tool calls (see
.claude/settings.json). It reads the hook input JSON on stdin and, to block,
prints a JSON decision on stdout and exits 0:

    {"hookSpecificOutput": {"hookEventName": "PreToolUse",
                            "permissionDecision": "deny",
                            "permissionDecisionReason": "..."}}

Claude sees the reason and can change its approach. The other documented way
to block is to print the reason on stderr and exit 2. Exit 1 does NOT block:
it's a non-blocking error and the tool call goes ahead.

To allow, the hook prints nothing and exits 0, which leaves the call to the
normal permission rules.

The decision logic is the pure function `decide()`, so it can be unit-tested
without Claude Code (tests/test_l7_hook.py).
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import PurePosixPath
from typing import Any

PROTECTED_DIR = "data"

# Tool input field that holds the target path, per file tool.
_PATH_FIELDS = {"Write": "file_path", "Edit": "file_path", "NotebookEdit": "notebook_path"}

# Best-effort Bash check: a command that names data/ and also looks like it
# writes, moves or deletes. A hook can't parse every shell trick (a Python
# one-liner that opens the file, for example), so this is a guard rail, not a
# sandbox. For OS-level enforcement, use Claude Code's sandbox.
_BASH_WRITE = re.compile(r"(>|\btee\b|\bsed\s+-i|\brm\b|\bmv\b|\bcp\b|\btruncate\b|\btouch\b|\bchmod\b|\bgit\s+(checkout|restore)\b)")
_BASH_DATA_PATH = re.compile(r"(^|[\s'\"=/])(\./)?data/")


def _normalize(path: str) -> str:
    """Use forward slashes so the check also works for Windows paths.

    A drive letter ("C:/...") becomes "/C:/..." so it counts as absolute.
    """
    path = path.replace("\\", "/")
    return "/" + path if re.match(r"^[A-Za-z]:/", path) else path


def is_protected(path: str, project_dir: str) -> bool:
    """True if `path` is inside <project_dir>/data/ (or is that directory)."""
    target = PurePosixPath(_normalize(path))
    root = PurePosixPath(_normalize(project_dir)) / PROTECTED_DIR
    if not target.is_absolute():
        target = PurePosixPath(_normalize(project_dir)) / target
    # Collapse "..", so "src/../data/x.json" can't sneak through.
    parts: list[str] = []
    for part in target.parts:
        if part == "..":
            if len(parts) > 1:
                parts.pop()
        elif part != ".":
            parts.append(part)
    resolved = PurePosixPath(*parts)
    return resolved == root or root in resolved.parents


def decide(hook_input: dict[str, Any], project_dir: str) -> str | None:
    """Return a denial reason if the tool call would change data/, else None."""
    tool = hook_input.get("tool_name", "")
    tool_input = hook_input.get("tool_input") or {}

    if tool in _PATH_FIELDS:
        path = tool_input.get(_PATH_FIELDS[tool], "")
        if path and is_protected(path, project_dir):
            return (
                f"{path} is a read-only fixture in {PROTECTED_DIR}/. "
                "Don't edit data files; change the code or the tests instead."
            )
        return None

    if tool == "Bash":
        command = tool_input.get("command", "")
        if _BASH_DATA_PATH.search(command) and _BASH_WRITE.search(command):
            return (
                f"This command looks like it would change files in {PROTECTED_DIR}/, "
                "which holds read-only fixtures. Read them, don't modify them."
            )
    return None


def deny_output(reason: str) -> dict[str, Any]:
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }


def main() -> int:
    hook_input = json.load(sys.stdin)
    # Claude Code exports CLAUDE_PROJECT_DIR to hooks; fall back to the cwd field.
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR") or hook_input.get("cwd") or os.getcwd()
    reason = decide(hook_input, project_dir)
    if reason:
        print(json.dumps(deny_output(reason)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
