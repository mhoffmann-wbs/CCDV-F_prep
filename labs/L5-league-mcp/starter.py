"""L5 starter: the League Stats MCP server.

Run from labs/:  uv run python L5-league-mcp/starter.py        (stdio; Ctrl+C to stop)
Check it with:   uv run python L5-league-mcp/l5_app.py --server L5-league-mcp/starter.py

get_injury_status is done as the worked example. Fill in the numbered TODOs in order.
The data functions are ready in l5_data.py. Stuck? Compare with solution.py.

A stdio server talks MCP over stdout: never print() here. Use `log` (stderr).
"""

import argparse
import logging
import sys
from typing import Annotated, Literal  # noqa: F401

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ResourceNotFoundError, ToolError  # noqa: F401
from mcp.types import ToolAnnotations
from pydantic import Field

from l5_data import SEASON, UnknownPlayerError, UnknownTeamError, injury_text, roster_text, schedule_text, stats_text, week_text  # noqa: F401

logging.basicConfig(stream=sys.stderr, level=logging.INFO, format="[league-stats] %(message)s")
log = logging.getLogger(__name__)

HTTP_HOST, HTTP_PORT = "127.0.0.1", 8765
SCHEDULE_URI = f"league://schedule/{SEASON}"
ROSTER_URI = "league://teams/{team}/roster"

server = MCPServer(
    "league-stats",
    instructions=(
        "Stats, injuries, schedule and rosters for a fictional four-team football league. "
        "Player ids look like POR-QB1. Fantasy points are full PPR."
    ),
)

READ_ONLY = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False)

PlayerIds = Annotated[
    list[str], Field(description='Exact player ids such as "POR-QB1". Ask for every player you need in one call.')
]


# Worked example: the docstring becomes the tool description, the type hints become the input schema.
@server.tool(annotations=READ_ONLY)
def get_injury_status(player_ids: PlayerIds) -> str:
    """Current injury designation (Out, Doubtful, Questionable, Full) and practice note for the given players.

    Call this for every player you are considering starting.
    """
    log.info("get_injury_status %s", player_ids)
    try:
        return injury_text(player_ids)
    except UnknownPlayerError as e:
        raise ToolError(str(e)) from e  # reaches Claude as an isError result it can act on


# TODO 1: the get_player_stats tool.
#   Same decorator. Parameters: player_ids: PlayerIds, detail: Literal["summary", "full"] = "summary".
#   Return stats_text(player_ids, detail). Turn UnknownPlayerError and ValueError into ToolError.
#   Write a docstring that says WHEN to call it, as in get_injury_status.


# TODO 2: the schedule resource.
#   @server.resource(SCHEDULE_URI, name="schedule", mime_type="text/plain", description=...)
#   returning schedule_text(). A resource is read-only context the HOST decides to attach.


# TODO 3: the team roster resource TEMPLATE.
#   @server.resource(ROSTER_URI, ...) on a function that takes `team: str` (the {team} in the URI)
#   and returns roster_text(team). Turn UnknownTeamError into ResourceNotFoundError.


# TODO 4: the weekly-preview prompt.
#   @server.prompt(name="weekly-preview", description=...) on a function taking `week: str`.
#   Return text that puts week_text(int(week)) inside <schedule> tags FIRST, then asks for a
#   fantasy preview that uses get_player_stats and get_injury_status for the facts.


def main() -> None:
    parser = argparse.ArgumentParser(description="League Stats MCP server (starter)")
    parser.add_argument("--http", action="store_true", help=f"serve Streamable HTTP on {HTTP_HOST}:{HTTP_PORT}")
    args = parser.parse_args()
    # TODO 5: when args.http is set, run server.run("streamable-http", host=HTTP_HOST, port=HTTP_PORT).
    #   Bind to 127.0.0.1, never 0.0.0.0, for a server without auth.
    _ = args
    log.info("stdio: waiting for a host on stdin")
    server.run()


if __name__ == "__main__":
    main()
