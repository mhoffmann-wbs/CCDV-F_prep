"""Offline tests for the data views and the custom tools."""

import asyncio

import pytest

from l6_data import UnknownTeamError, format_injuries, format_plays, format_stats, report_path, team_name
from l6_tools import ALL_TOOLS, get_injuries, get_plays, tool_name


def test_report_path_is_inside_reports():
    p = report_path("NSH")
    assert p.parent.name == "reports" and p.name == "nsh-scouting.md"


def test_stats_cover_only_the_team():
    text = format_stats("NSH")
    assert "Quentin Mbeki" in text and "Marcus Holloway" not in text
    assert "totals:" in text and "W1:" in text


def test_injuries_name_the_player():
    assert "Darius Kincaid (WR): Out" in format_injuries("NSH")


def test_plays_filter_by_side_and_quarter():
    offense = format_plays("NSH", side="offense")
    defense = format_plays("NSH", side="defense")
    every = format_plays("NSH")
    assert " NSH ball" in offense and " POR ball" not in offense
    assert " POR ball" in defense and " NSH ball" not in defense
    assert len(every.splitlines()) == len(offense.splitlines()) + len(defense.splitlines()) - 1
    q4 = format_plays("NSH", quarter=4)
    assert all(line.startswith("- Q4") for line in q4.splitlines()[1:])


def test_team_without_film_says_so():
    assert format_plays("SAC").startswith("No play-by-play film")


def test_unknown_team_raises():
    with pytest.raises(UnknownTeamError):
        team_name("XXX")


def test_tools_are_read_only_and_named_for_the_server():
    assert tool_name("get_plays") == "mcp__gridiron__get_plays"
    for t in ALL_TOOLS:
        assert t.annotations is not None
        assert getattr(t.annotations, "readOnlyHint", None) or getattr(t.annotations, "read_only_hint", None)


def test_tool_handlers_return_text_and_errors():
    ok = asyncio.run(get_plays.handler({"team": "nsh", "side": "offense"}))
    assert "NSH ball" in ok["content"][0]["text"] and not ok.get("is_error")
    bad = asyncio.run(get_injuries.handler({"team": "XXX"}))
    assert bad["is_error"] is True and "Unknown team" in bad["content"][0]["text"]
