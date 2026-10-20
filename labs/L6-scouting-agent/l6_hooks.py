"""L6 guardrail: a PreToolUse hook that denies any file write outside reports/.

The path check is a pure function (`write_denial_reason`) so it can be unit-tested
without the Agent SDK, a CLI process or an API key. The async callback around it is
what the SDK calls before every matching tool use.

Why a hook and not a sentence in the system prompt? A prompt asks; a hook guarantees.
It runs in your process before the tool, every time, and a hook `deny` holds in every
permission mode, including bypassPermissions. PostToolUse would be too late: the file
would already be written.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

# Built-in tools that write files, and the input key that holds the target path.
WRITE_TOOLS: dict[str, str] = {"Write": "file_path", "Edit": "file_path", "NotebookEdit": "notebook_path"}

# The matcher is a regex on the tool NAME (it never sees paths). Bash is not covered,
# which is why the agent doesn't get Bash at all.
WRITE_MATCHER = "Write|Edit|NotebookEdit"


def write_denial_reason(tool_name: str, tool_input: dict[str, Any], cwd: Path, reports_dir: Path) -> str | None:
    """Return why this call must be denied, or None if it may go ahead.

    - Relative paths are resolved against the agent's working directory.
    - `..` segments and symlinks are resolved before the check, so
      `reports/../solution.py` or a symlink inside reports/ can't escape.
    - The reports/ directory itself is not a valid file target.
    """
    key = WRITE_TOOLS.get(tool_name)
    if key is None:
        return None  # not a write tool; other guards (allowed_tools, permission mode) apply
    raw = tool_input.get(key)
    if not isinstance(raw, str) or not raw.strip():
        return f"{tool_name} call has no {key}; refusing to guess where it writes."
    target = Path(raw).expanduser()
    if not target.is_absolute():
        target = cwd / target
    target = target.resolve()
    allowed_root = reports_dir.resolve()
    if target != allowed_root and target.is_relative_to(allowed_root):
        return None
    return f"Writes are only allowed under {allowed_root}/ (got {target}). Save the report in reports/."


def deny(reason: str) -> dict[str, Any]:
    """The documented PreToolUse deny output: hookSpecificOutput.permissionDecision = "deny"."""
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }


def make_reports_guard(reports_dir: Path):
    """Build the async hook callback for ClaudeAgentOptions(hooks={"PreToolUse": [...]})."""

    async def guard_reports(input_data: dict[str, Any], tool_use_id: str | None, context: Any) -> dict[str, Any]:
        if input_data.get("hook_event_name") != "PreToolUse":
            return {}
        reason = write_denial_reason(
            input_data.get("tool_name", ""),
            input_data.get("tool_input") or {},
            Path(input_data.get("cwd") or "."),
            reports_dir,
        )
        return {} if reason is None else deny(reason)  # {} = no objection

    return guard_reports
