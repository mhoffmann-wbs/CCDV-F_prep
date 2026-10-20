"""Offline tests for the reports/ guardrail (no SDK process, no API key)."""

import asyncio
from pathlib import Path

import pytest

from l6_hooks import WRITE_MATCHER, deny, make_reports_guard, write_denial_reason


@pytest.fixture
def lab(tmp_path: Path) -> tuple[Path, Path]:
    reports = tmp_path / "reports"
    reports.mkdir()
    return tmp_path, reports


@pytest.mark.parametrize("path", ["reports/nsh-scouting.md", "reports/notes/nsh-notes.md", "./reports/x.md"])
def test_allows_writes_inside_reports(lab, path):
    cwd, reports = lab
    assert write_denial_reason("Write", {"file_path": path}, cwd, reports) is None


def test_allows_absolute_path_inside_reports(lab):
    cwd, reports = lab
    assert write_denial_reason("Edit", {"file_path": str(reports / "a.md")}, cwd, reports) is None


@pytest.mark.parametrize(
    "path",
    [
        "solution.py",
        "reports/../solution.py",  # traversal
        "reports",  # the folder itself is not a file
        "reportsX/evil.md",  # prefix trick: not inside reports/
        "/etc/passwd",
        "../gridiron/data.py",
    ],
)
def test_denies_writes_outside_reports(lab, path):
    cwd, reports = lab
    reason = write_denial_reason("Write", {"file_path": path}, cwd, reports)
    assert reason and "reports" in reason


def test_denies_symlink_escape(lab, tmp_path_factory):
    cwd, reports = lab
    outside = tmp_path_factory.mktemp("outside")
    (reports / "link").symlink_to(outside, target_is_directory=True)
    assert write_denial_reason("Write", {"file_path": "reports/link/x.md"}, cwd, reports)


def test_notebook_edit_uses_notebook_path(lab):
    cwd, reports = lab
    assert write_denial_reason("NotebookEdit", {"notebook_path": "a.ipynb"}, cwd, reports)
    assert write_denial_reason("NotebookEdit", {"notebook_path": "reports/a.ipynb"}, cwd, reports) is None


def test_missing_path_is_denied_and_other_tools_pass(lab):
    cwd, reports = lab
    assert write_denial_reason("Write", {}, cwd, reports)
    assert write_denial_reason("Read", {"file_path": "/etc/passwd"}, cwd, reports) is None


def test_matcher_covers_every_write_tool():
    assert set(WRITE_MATCHER.split("|")) == {"Write", "Edit", "NotebookEdit"}


def test_deny_uses_documented_pretooluse_shape():
    out = deny("nope")
    assert out == {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": "nope",
        }
    }


def test_callback_denies_outside_and_allows_inside(lab):
    cwd, reports = lab
    guard = make_reports_guard(reports)

    def call(path: str) -> dict:
        data = {"hook_event_name": "PreToolUse", "tool_name": "Write", "tool_input": {"file_path": path}, "cwd": str(cwd)}
        return asyncio.run(guard(data, "toolu_1", {"signal": None}))

    assert call("reports/ok.md") == {}
    assert call("playbook.md")["hookSpecificOutput"]["permissionDecision"] == "deny"
