"""L5 data: the season schedule and team rosters, plus L4's stats and injury views.

The MCP server doesn't reimplement anything. It wraps the same functions that
L4's custom tools call, which is the usual path from "a tool one app needs" to
"a server several apps share". L4's folder is put on the path explicitly so the
server also runs as a subprocess launched by Claude Code, outside pytest.
"""

from __future__ import annotations

import sys
from pathlib import Path

from gridiron.data import load_game, load_injuries, load_players, load_teams

LAB_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(LAB_DIR.parent / "L4-lineup-assistant"))

from l4_league import UnknownPlayerError, injury_text, stats_text  # noqa: E402

__all__ = ["SCHEDULE", "UnknownPlayerError", "UnknownTeamError", "injury_text", "roster_text", "schedule_text", "stats_text", "week_text"]

SEASON = 2026

# (week, away, home). Every team plays once a week; weeks 4-6 repeat weeks 1-3
# with home and away swapped. Week 3 is the game in the play-by-play fixture.
SCHEDULE: list[tuple[int, str, str]] = [
    (1, "SAC", "POR"), (1, "BAL", "NSH"),
    (2, "POR", "BAL"), (2, "NSH", "SAC"),
    (3, "POR", "NSH"), (3, "BAL", "SAC"),
    (4, "POR", "SAC"), (4, "NSH", "BAL"),
    (5, "BAL", "POR"), (5, "SAC", "NSH"),
    (6, "NSH", "POR"), (6, "SAC", "BAL"),
]  # fmt: skip

WEEKS = sorted({w for w, _, _ in SCHEDULE})


class UnknownTeamError(ValueError):
    pass


def _team_names() -> dict[str, str]:
    return {t.id: t.name for t in load_teams()}


def _results() -> dict[tuple[int, str, str], str]:
    """Final scores we have play-by-play for, keyed like SCHEDULE."""
    game = load_game()
    score = f"final {game.away} {game.final_score[game.away]} - {game.home} {game.final_score[game.home]}"
    return {(game.week, game.away, game.home): score}


def week_text(week: int) -> str:
    if week not in WEEKS:
        raise ValueError(f"week must be one of {WEEKS[0]}-{WEEKS[-1]}, got {week}")
    names, results = _team_names(), _results()
    lines = []
    for game in (g for g in SCHEDULE if g[0] == week):
        _, away, home = game
        result = f" ({results[game]})" if game in results else ""
        lines.append(f"Week {week}: {names[away]} ({away}) at {names[home]} ({home}){result}")
    return "\n".join(lines)


def schedule_text() -> str:
    return f"{SEASON} season schedule (away at home)\n" + "\n".join(week_text(w) for w in WEEKS)


def roster_text(team: str) -> str:
    """One NFL team's players with position and injury tag (not your fantasy roster)."""
    team = team.upper()
    names = _team_names()
    if team not in names:
        raise UnknownTeamError(f"Unknown team {team!r}. Teams: {', '.join(sorted(names))}.")
    injuries = {i.player_id: i.designation for i in load_injuries()}
    lines = [f"{names[team]} ({team}) roster"]
    for p in (p for p in load_players() if p.team == team):
        tag = f" [{injuries[p.id]}]" if p.id in injuries else ""
        lines.append(f"{p.id} | {p.name} | {p.position}{tag}")
    return "\n".join(lines)
