"""L4 tool definitions and the dispatcher that runs them.

Design choices worth copying:
- Descriptions say WHEN to call a tool, not only what it does. Claude decides
  from the description alone.
- `strict: True` on every tool: the API guarantees the input matches the schema
  (every object sets additionalProperties: false and lists all its properties
  in required). That's the shape; facts are still checked in code.
- No numeric limits (minItems, minimum, ...) in the schemas. Strict tool use
  doesn't support every JSON Schema keyword, so limits live in code.
- Errors are results, not exceptions: an unknown id or a broken lineup goes
  back to Claude as a tool_result with is_error=True, so it can fix the call.
- set_lineup is the only tool with a side effect, and it runs only after a
  human approves the exact lineup.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from anthropic.types import ToolParam

from l4_league import (
    SLOTS,
    UPCOMING_WEEK,
    LineupStore,
    UnknownPlayerError,
    format_lineup,
    injury_text,
    roster_text,
    stats_text,
    validate_lineup,
)

PLAYER_IDS = {
    "type": "array",
    "items": {"type": "string"},
    "description": 'Exact player ids such as "POR-QB1". Ask for every player you need in one call.',
}

TOOLS: list[ToolParam] = [
    {
        "name": "get_roster",
        "description": (
            "List the user's fantasy roster: player id, name, position, NFL team and any injury tag. "
            "Call this first whenever you need to know who the user can start."
        ),
        "strict": True,
        "input_schema": {"type": "object", "properties": {}, "required": [], "additionalProperties": False},
    },
    {
        "name": "get_player_stats",
        "description": (
            "Fantasy points (full PPR) per week and the season average for the given players. "
            "Call this before comparing players or choosing starters. Use detail=summary unless the user "
            "asks why a player scored what he did; detail=full adds raw stat lines and costs more context."
        ),
        "strict": True,
        "input_schema": {
            "type": "object",
            "properties": {
                "player_ids": PLAYER_IDS,
                "detail": {"type": "string", "enum": ["summary", "full"]},
            },
            "required": ["player_ids", "detail"],
            "additionalProperties": False,
        },
    },
    {
        "name": "get_injury_status",
        "description": (
            "Current injury designation (Out, Doubtful, Questionable, Full) and practice note for the given "
            "players. Call this for every player you are considering starting before you propose a lineup."
        ),
        "strict": True,
        "input_schema": {
            "type": "object",
            "properties": {"player_ids": PLAYER_IDS},
            "required": ["player_ids"],
            "additionalProperties": False,
        },
    },
    {
        "name": "set_lineup",
        "description": (
            f"Save the starting lineup for week {UPCOMING_WEEK}. This changes the user's team, and the user "
            "must approve it, so call it once, only after you have checked stats and injuries for every "
            "starter. If it returns an error, fix the problems it lists and call it again."
        ),
        "strict": True,
        "input_schema": {
            "type": "object",
            "properties": {
                "week": {"type": "integer", "description": f"Always {UPCOMING_WEEK}, the upcoming week."},
                "lineup": {
                    "type": "object",
                    "description": "One exact player id per starting slot. FLEX takes an RB, WR or TE.",
                    "properties": {slot: {"type": "string"} for slot in SLOTS},
                    "required": list(SLOTS),
                    "additionalProperties": False,
                },
                "rationale": {"type": "string", "description": "Two or three sentences the user will read."},
            },
            "required": ["week", "lineup", "rationale"],
            "additionalProperties": False,
        },
    },
]

TOOL_NAMES = [t["name"] for t in TOOLS]

SYSTEM_PROMPT = f"""\
You are the lineup assistant for a full-PPR fantasy football team in a fictional league. \
The upcoming week is week {UPCOMING_WEEK}.

How to work:
- Get facts from the tools; never guess a player's stats, position or injury status.
- When you need several independent facts, request them in the same turn (for example \
stats and injuries together) instead of one call per turn.
- A player ruled Out can't start. Treat Doubtful as a likely no and Questionable as a \
judgment call you explain.
- When the user asks you to set the lineup, call set_lineup once with your final choice. \
The user approves it before anything is saved. If they decline, ask what to change.
- Finish with a short summary: the starters, and one line on each close call."""

# Safe to run concurrently: no side effects, no shared state.
READ_ONLY = frozenset({"get_roster", "get_player_stats", "get_injury_status"})

# Shows the user the exact change and returns True to go ahead.
Approver = Callable[[str], bool]


@dataclass
class ToolOutcome:
    content: str
    is_error: bool = False


def run_tool(name: str, args: dict[str, Any], *, approve: Approver, store: LineupStore) -> ToolOutcome:
    """Run one tool call. Never raises for a bad call: problems come back as is_error results."""
    try:
        if name == "get_roster":
            return ToolOutcome(roster_text())
        if name == "get_player_stats":
            return ToolOutcome(stats_text(list(args["player_ids"]), args.get("detail", "summary")))
        if name == "get_injury_status":
            return ToolOutcome(injury_text(list(args["player_ids"])))
        if name == "set_lineup":
            return _set_lineup(args, approve=approve, store=store)
    except (UnknownPlayerError, ValueError, KeyError, TypeError) as e:
        return ToolOutcome(f"Error: {e}", is_error=True)
    return ToolOutcome(f"Error: unknown tool {name!r}. Available tools: {', '.join(TOOL_NAMES)}.", is_error=True)


def _set_lineup(args: dict[str, Any], *, approve: Approver, store: LineupStore) -> ToolOutcome:
    week, lineup, rationale = int(args["week"]), dict(args["lineup"]), str(args["rationale"])
    # Validate BEFORE asking: never make a human approve something that breaks the rules.
    problems = validate_lineup(week, lineup)
    if problems:
        return ToolOutcome("Lineup rejected, nothing was saved:\n- " + "\n- ".join(problems), is_error=True)

    preview = f"Week {week} lineup:\n{format_lineup(lineup)}\nWhy: {rationale}"
    if not approve(preview):
        return ToolOutcome(
            "The user declined this lineup, nothing was saved. Ask what they want to change.", is_error=True
        )
    path = store.save(week, lineup, rationale)
    return ToolOutcome(f"Lineup saved to {path.name}.")


def tool_result(tool_use_id: str, outcome: ToolOutcome) -> dict[str, Any]:
    """The tool_result block for one call. Its tool_use_id must match the call's id."""
    block: dict[str, Any] = {"type": "tool_result", "tool_use_id": tool_use_id, "content": outcome.content}
    if outcome.is_error:
        block["is_error"] = True
    return block
