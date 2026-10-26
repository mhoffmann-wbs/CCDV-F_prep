"""Offline tests for the League Stats MCP server, through a real MCP client connected in-process."""

import importlib.util
from pathlib import Path

import anyio
import pytest
from l5_data import SCHEDULE, WEEKS, roster_text, schedule_text, week_text
from mcp import Client, MCPError

_spec = importlib.util.spec_from_file_location("l5_solution", Path(__file__).with_name("solution.py"))
solution = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(solution)


def with_client(fn):
    """Run `fn(client)` against the solution server, connected in-process."""

    async def main():
        async with Client(solution.server) as client:
            return await fn(client)

    return anyio.run(main)


def test_schedule_has_every_team_once_a_week_and_matches_the_fixture():
    for week in WEEKS:
        teams = [t for w, away, home in SCHEDULE if w == week for t in (away, home)]
        assert sorted(teams) == ["BAL", "NSH", "POR", "SAC"], week
    assert "Portland Lumberjacks (POR) at Nashville Night Owls (NSH) (final POR 24 - NSH 20)" in week_text(3)
    assert schedule_text().count("\n") == len(SCHEDULE)
    with pytest.raises(ValueError):
        week_text(9)


def test_tools_are_the_read_only_pair_with_when_to_call_descriptions():
    tools = with_client(lambda c: c.list_tools())
    by_name = {t.name: t for t in tools.tools}
    assert set(by_name) == {"get_player_stats", "get_injury_status"}  # no write tool on a shared server
    for tool in by_name.values():
        assert tool.annotations.read_only_hint is True
        assert "Call this" in tool.description
        assert tool.input_schema["required"] == ["player_ids"]
    assert by_name["get_player_stats"].input_schema["properties"]["detail"]["enum"] == ["summary", "full"]


def test_tool_call_returns_text_and_unknown_ids_return_an_error_result():
    async def calls(c):
        ok = await c.call_tool("get_player_stats", {"player_ids": ["POR-QB1"]})
        bad = await c.call_tool("get_injury_status", {"player_ids": ["POR-QB9"]})
        return ok, bad

    ok, bad = with_client(calls)
    assert not ok.is_error and "W3 25.34" in ok.content[0].text
    assert bad.is_error and "POR-QB9" in bad.content[0].text and "get_roster" in bad.content[0].text


def test_schedule_resource_and_roster_template():
    async def reads(c):
        listed = await c.list_resources()
        templates = await c.list_resource_templates()
        schedule = await c.read_resource(solution.SCHEDULE_URI)
        roster = await c.read_resource("league://teams/nsh/roster")
        return listed, templates, schedule, roster

    listed, templates, schedule, roster = with_client(reads)
    assert [str(r.uri) for r in listed.resources] == [solution.SCHEDULE_URI]
    assert [t.uri_template for t in templates.resource_templates] == [solution.ROSTER_URI]
    assert schedule.contents[0].text == schedule_text()
    assert roster.contents[0].text == roster_text("NSH")
    assert "NSH-WR1 | Darius Kincaid | WR [Out]" in roster.contents[0].text


def test_unknown_team_is_a_not_found_error():
    async def read(c):
        with pytest.raises(MCPError, match="Unknown team 'XYZ'"):
            await c.read_resource("league://teams/XYZ/roster")

    with_client(read)


def test_weekly_preview_prompt_puts_the_schedule_first():
    async def prompt(c):
        return await c.list_prompts(), await c.get_prompt("weekly-preview", {"week": "4"})

    listed, result = with_client(prompt)
    (p,) = listed.prompts
    assert p.name == "weekly-preview" and [a.name for a in p.arguments] == ["week"]
    text = result.messages[0].content.text
    assert text.startswith("<schedule>\nWeek 4:")
    assert text.index("</schedule>") < text.index("get_player_stats")


def test_server_never_prints_to_stdout():
    # stdout is the protocol channel of a stdio server; logs must go to stderr.
    source = Path(solution.__file__).read_text()
    assert "print(" not in source
