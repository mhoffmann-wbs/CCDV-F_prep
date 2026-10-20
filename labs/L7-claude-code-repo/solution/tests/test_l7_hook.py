"""Offline tests for the PreToolUse hook in .claude/hooks/protect_data.py.

No Claude Code needed: decide() is a pure function, and main() is driven
through stdin the same way Claude Code drives it.
"""

import importlib.util
import io
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HOOK_PATH = ROOT / ".claude" / "hooks" / "protect_data.py"

# A unique module name so it can't clash with another lab's hook module.
_spec = importlib.util.spec_from_file_location("l7_protect_data_hook", HOOK_PATH)
assert _spec and _spec.loader
hook = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(hook)

PROJECT = "/work/gridiron-stats"


def event(tool: str, **tool_input: object) -> dict:
    return {"hook_event_name": "PreToolUse", "tool_name": tool, "tool_input": tool_input, "cwd": PROJECT}


@pytest.mark.parametrize(
    "tool_input",
    [
        event("Edit", file_path=f"{PROJECT}/data/players.json", old_string="1", new_string="2"),
        event("Write", file_path=f"{PROJECT}/data/new.json", content="{}"),
        event("Write", file_path=f"{PROJECT}/gridiron_stats/../data/games.json", content="{}"),
        event("NotebookEdit", notebook_path=f"{PROJECT}/data/scratch.ipynb"),
        event("Edit", file_path="C:\\work\\gridiron-stats\\data\\players.json"),
        event("Bash", command="echo '[]' > data/players.json"),
        event("Bash", command="sed -i '' 's/20/21/' ./data/games.json"),
        event("Bash", command="rm data/teams.json"),
    ],
)
def test_blocks_changes_to_data(tool_input):
    project = "C:\\work\\gridiron-stats" if "C:" in json.dumps(tool_input) else PROJECT
    assert hook.decide(tool_input, project) is not None


@pytest.mark.parametrize(
    "tool_input",
    [
        event("Edit", file_path=f"{PROJECT}/gridiron_stats/fantasy.py"),
        event("Write", file_path=f"{PROJECT}/tests/test_l7_new.py", content=""),
        event("Write", file_path=f"{PROJECT}/database/x.json", content=""),  # "database" isn't "data"
        event("Read", file_path=f"{PROJECT}/data/players.json"),  # reading is fine
        event("Bash", command="cat data/players.json"),
        event("Bash", command="uv run pytest"),
        event("Bash", command="python -m json.tool data/games.json"),
    ],
)
def test_allows_everything_else(tool_input):
    assert hook.decide(tool_input, PROJECT) is None


def run_main(monkeypatch, capsys, payload: dict) -> tuple[int, str]:
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", PROJECT)
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
    code = hook.main()
    return code, capsys.readouterr().out


def test_main_prints_documented_deny_json(monkeypatch, capsys):
    code, out = run_main(monkeypatch, capsys, event("Edit", file_path=f"{PROJECT}/data/players.json"))
    assert code == 0
    decision = json.loads(out)["hookSpecificOutput"]
    assert decision["hookEventName"] == "PreToolUse"
    assert decision["permissionDecision"] == "deny"
    assert "read-only" in decision["permissionDecisionReason"]


def test_main_is_silent_when_allowed(monkeypatch, capsys):
    code, out = run_main(monkeypatch, capsys, event("Edit", file_path=f"{PROJECT}/gridiron_stats/fantasy.py"))
    assert (code, out) == (0, "")


def test_settings_register_the_hook():
    settings = json.loads((ROOT / ".claude" / "settings.json").read_text())
    group = settings["hooks"]["PreToolUse"][0]
    assert set(group["matcher"].split("|")) >= {"Write", "Edit", "Bash"}
    handler = group["hooks"][0]
    assert handler["type"] == "command"
    assert handler["args"] == ["${CLAUDE_PROJECT_DIR}/.claude/hooks/protect_data.py"]
    assert handler["onFailure"] == "block"


def test_plugin_copies_match_the_project_files():
    plugin = ROOT / "plugin" / "gridiron-tools"
    if not plugin.exists():
        pytest.skip("no plugin/ folder yet (lab step 7)")
    pairs = [
        (HOOK_PATH, plugin / "scripts" / "protect_data.py"),
        (ROOT / ".claude" / "skills" / "game-preview" / "SKILL.md", plugin / "skills" / "game-preview" / "SKILL.md"),
        (ROOT / ".claude" / "agents" / "test-runner.md", plugin / "agents" / "test-runner.md"),
    ]
    for original, copy in pairs:
        assert original.read_text() == copy.read_text(), f"{copy} is out of date"
