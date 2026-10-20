"""Offline tests for the solution wiring: workflow prompts and agent options. No API calls."""

import importlib.util
from pathlib import Path

from l6_hooks import WRITE_MATCHER
from l6_prompts import REPORT_SECTIONS

_spec = importlib.util.spec_from_file_location("l6_solution", Path(__file__).with_name("solution.py"))
solution = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(solution)


def test_workflow_gathers_everything_in_code():
    data = solution.gather("NSH")
    assert data["name"] == "Nashville Night Owls"
    assert {"stats", "injuries", "plays"} <= data.keys()


def test_workflow_prompts_tag_inputs_and_list_sections():
    film, report = solution.build_workflow_prompts(solution.gather("NSH"))
    assert film.startswith("<film>") and "</film>" in film
    for tag in ("<stats>", "<injuries>", "<film_notes>"):
        assert tag in report
    assert all(f"## {s}" in report for s in REPORT_SECTIONS)
    assert "{film_notes}" in report  # filled in after the first call


def test_agent_options_are_least_privilege():
    o = solution.build_options("NSH")
    assert o.tools == ["Agent", "Read", "Write"]  # no Bash, no Edit
    assert "Bash" not in o.allowed_tools and "Read" not in o.allowed_tools
    assert o.permission_mode == "dontAsk"
    assert o.setting_sources == []
    assert isinstance(o.system_prompt, str) and "reports/" in o.system_prompt
    assert o.max_budget_usd and o.max_turns


def test_agent_has_film_and_stats_subagents_with_narrow_tools():
    agents = solution.build_options("NSH").agents
    assert set(agents) == {"film", "stats"}
    assert agents["film"].tools == ["mcp__gridiron__get_plays"]
    assert set(agents["stats"].tools) == {"mcp__gridiron__get_player_stats", "mcp__gridiron__get_injuries"}


def test_agent_registers_the_pretooluse_write_guard():
    hooks = solution.build_options("NSH").hooks
    (matcher,) = hooks["PreToolUse"]
    assert matcher.matcher == WRITE_MATCHER and len(matcher.hooks) == 1
    assert "gridiron" in solution.build_options("NSH").mcp_servers


def test_no_credentials_means_no_calls(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    assert solution.has_credentials() is False
