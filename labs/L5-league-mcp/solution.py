"""L5 reference solution: the League Stats MCP server.

One server, three primitives:
  tools      get_player_stats, get_injury_status   (model-controlled: Claude decides to call)
  resources  league://schedule/2026                 (application-controlled: the host attaches it)
             league://teams/{team}/roster           (a resource template)
  prompts    weekly-preview                         (user-controlled: a slash command in Claude Code)

Run from labs/:
  uv run python L5-league-mcp/solution.py           # stdio: a host launches it as a subprocess
  uv run python L5-league-mcp/solution.py --http    # Streamable HTTP on http://127.0.0.1:8765/mcp

A stdio server talks MCP over stdout, so it must never print anything there.
Diagnostics go to stderr through `logging`.
"""

import argparse
import logging
import sys
from typing import Annotated, Literal

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ResourceNotFoundError, ToolError
from mcp.types import ToolAnnotations
from pydantic import Field

from l5_data import SEASON, UnknownPlayerError, UnknownTeamError, injury_text, roster_text, schedule_text, stats_text, week_text

logging.basicConfig(stream=sys.stderr, level=logging.INFO, format="[league-stats] %(message)s")
log = logging.getLogger(__name__)

HTTP_HOST, HTTP_PORT = "127.0.0.1", 8765  # loopback only: never expose a dev server on all interfaces
SCHEDULE_URI = f"league://schedule/{SEASON}"
ROSTER_URI = "league://teams/{team}/roster"

server = MCPServer(
    "league-stats",
    instructions=(
        "Stats, injuries, schedule and rosters for a fictional four-team football league. "
        "Player ids look like POR-QB1. Fantasy points are full PPR."
    ),
)

# Read-only, no side effects: hosts may run these calls in parallel and without asking.
READ_ONLY = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False)

PlayerIds = Annotated[
    list[str], Field(description='Exact player ids such as "POR-QB1". Ask for every player you need in one call.')
]


# --------------------------------------------------------------------------- #
# Tools: the same functions L4 called, now behind a protocol any host can use.
# --------------------------------------------------------------------------- #


@server.tool(annotations=READ_ONLY)
def get_player_stats(player_ids: PlayerIds, detail: Literal["summary", "full"] = "summary") -> str:
    """Fantasy points (full PPR) per week and the season average for the given players.

    Call this before comparing players or choosing starters. Use detail="summary" unless the
    user asks why a player scored what he did; "full" adds raw stat lines and costs more context.
    """
    log.info("get_player_stats %s %s", player_ids, detail)
    try:
        return stats_text(player_ids, detail)
    except (UnknownPlayerError, ValueError) as e:
        # ToolError reaches Claude as an isError result with this message; any other
        # exception would reach it as a generic failure with the details withheld.
        raise ToolError(str(e)) from e


@server.tool(annotations=READ_ONLY)
def get_injury_status(player_ids: PlayerIds) -> str:
    """Current injury designation (Out, Doubtful, Questionable, Full) and practice note for the given players.

    Call this for every player you are considering starting.
    """
    log.info("get_injury_status %s", player_ids)
    try:
        return injury_text(player_ids)
    except UnknownPlayerError as e:
        raise ToolError(str(e)) from e


# --------------------------------------------------------------------------- #
# Resources: read-only context the host (or the user) chooses to attach.
# --------------------------------------------------------------------------- #


@server.resource(SCHEDULE_URI, name="schedule", mime_type="text/plain", description=f"The {SEASON} season schedule.")
def schedule() -> str:
    return schedule_text()


@server.resource(ROSTER_URI, name="team-roster", mime_type="text/plain", description="One team's players and injury tags.")
def team_roster(team: str) -> str:
    try:
        return roster_text(team)
    except UnknownTeamError as e:
        raise ResourceNotFoundError(str(e)) from e


# --------------------------------------------------------------------------- #
# Prompts: a reusable request the user invokes on purpose (/mcp__league__weekly-preview 4).
# --------------------------------------------------------------------------- #


@server.prompt(name="weekly-preview", description="Preview one week's games for a fantasy manager.")
def weekly_preview(week: Annotated[str, Field(description="Week number from the schedule, 1-6.")]) -> str:
    try:
        games = week_text(int(week))
    except ValueError as e:
        raise ValueError(f"week must be a number from the schedule: {e}") from e
    return (
        f"<schedule>\n{games}\n</schedule>\n\n"
        f"Preview week {week} for a full-PPR fantasy manager. For each game, name the two or three "
        "players most worth starting and anyone whose injury status makes them risky. Use "
        "get_player_stats and get_injury_status for the facts; don't guess numbers. Keep it under 250 words."
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="League Stats MCP server")
    parser.add_argument("--http", action="store_true", help=f"serve Streamable HTTP on {HTTP_HOST}:{HTTP_PORT}")
    args = parser.parse_args()
    if args.http:
        log.info("Streamable HTTP on http://%s:%s/mcp", HTTP_HOST, HTTP_PORT)
        server.run("streamable-http", host=HTTP_HOST, port=HTTP_PORT)
    else:
        log.info("stdio: waiting for a host on stdin")
        server.run()


if __name__ == "__main__":
    main()
