"""L6 custom tools: an in-process SDK MCP server named "gridiron" over l6_data.

Why custom tools instead of letting the agent Read the fixture files?
- Least privilege: the agent never gets a file-system read tool for the data,
  so it can't wander into other files. Each tool answers one question.
- Pruned output: the tools return compact text (and can filter by side and
  quarter), not raw JSON, which keeps subagent context small (skill 6.1).
- Same data path as the workflow, so the comparison measures the design, not the data.

Claude sees these as mcp__gridiron__get_player_stats, mcp__gridiron__get_injuries
and mcp__gridiron__get_plays.
"""

from __future__ import annotations

from typing import Any

from claude_agent_sdk import ToolAnnotations, create_sdk_mcp_server, tool

from l6_data import UnknownTeamError, format_injuries, format_plays, format_stats

SERVER_NAME = "gridiron"
READ_ONLY = ToolAnnotations(readOnlyHint=True)  # no side effects, so calls may run in parallel


def _text(text: str) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": text}]}


def _error(text: str) -> dict[str, Any]:
    # Errors are results: Claude reads this message and can change course.
    return {"content": [{"type": "text", "text": text}], "is_error": True}


@tool(
    "get_player_stats",
    "Season totals and week-by-week stats for every player on one team. Input: team id such as NSH.",
    {"team": str},
    annotations=READ_ONLY,
)
async def get_player_stats(args: dict[str, Any]) -> dict[str, Any]:
    try:
        return _text(format_stats(str(args["team"]).upper()))
    except UnknownTeamError as e:
        return _error(str(e))


@tool(
    "get_injuries",
    "Current injury designations (Out, Doubtful, Questionable, Full) for one team's players.",
    {"team": str},
    annotations=READ_ONLY,
)
async def get_injuries(args: dict[str, Any]) -> dict[str, Any]:
    try:
        return _text(format_injuries(str(args["team"]).upper()))
    except UnknownTeamError as e:
        return _error(str(e))


@tool(
    "get_plays",
    "Play-by-play film for one team's games. Filter with side (offense, defense, all) and quarter (1-4) "
    "to read only what you need.",
    {
        "type": "object",
        "properties": {
            "team": {"type": "string", "description": "Team id such as NSH"},
            "side": {"type": "string", "enum": ["offense", "defense", "all"]},
            "quarter": {"type": "integer", "minimum": 1, "maximum": 4},
        },
        "required": ["team"],
    },
    annotations=READ_ONLY,
)
async def get_plays(args: dict[str, Any]) -> dict[str, Any]:
    try:
        return _text(format_plays(str(args["team"]).upper(), args.get("side", "all"), args.get("quarter")))
    except (UnknownTeamError, ValueError) as e:
        return _error(str(e))


ALL_TOOLS = [get_player_stats, get_injuries, get_plays]


def tool_name(name: str) -> str:
    """Fully qualified name as Claude and allowed_tools see it: mcp__<server>__<tool>."""
    return f"mcp__{SERVER_NAME}__{name}"


def build_server():
    return create_sdk_mcp_server(name=SERVER_NAME, version="1.0.0", tools=ALL_TOOLS)
