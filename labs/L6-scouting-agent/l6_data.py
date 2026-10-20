"""L6 data helpers: compact, text-ready views of one team's stats, injuries and film.

Both versions of the lab use these, so the comparison is fair:
- Part A (the workflow) calls them directly, in a fixed order.
- Part B (the agent) reaches them through the custom tools in l6_tools.py.

Each helper returns only what a scout needs (pruned at the source, skill 6.1),
not the raw fixture JSON.
"""

from __future__ import annotations

from pathlib import Path

from gridiron.data import FIXTURES, Game, Play, Player, load_game, load_injuries, load_players, load_teams

LAB_DIR = Path(__file__).resolve().parent
REPORTS_DIR = LAB_DIR / "reports"

STAT_FIELDS = [
    "passing_yds",
    "passing_td",
    "interceptions",
    "rushing_yds",
    "rushing_td",
    "receptions",
    "receiving_yds",
    "receiving_td",
    "field_goals_made",
    "extra_points_made",
]


class UnknownTeamError(ValueError):
    """Raised for a team id that isn't in teams.json."""


def team_ids() -> list[str]:
    return [t.id for t in load_teams()]


def team_name(team: str) -> str:
    for t in load_teams():
        if t.id == team:
            return t.name
    raise UnknownTeamError(f"Unknown team {team!r}. Known teams: {', '.join(team_ids())}")


def report_path(team: str) -> Path:
    """Where the scouting report for `team` goes: reports/<team>-scouting.md."""
    return REPORTS_DIR / f"{team.lower()}-scouting.md"


def team_players(team: str) -> list[Player]:
    team_name(team)  # validates the id
    return [p for p in load_players() if p.team == team]


def season_totals(player: Player) -> dict[str, int]:
    """Sum every non-empty stat over the weeks played."""
    totals: dict[str, int] = {}
    for week in player.weekly_stats:
        for field in STAT_FIELDS:
            value = getattr(week, field)
            if value is not None:
                totals[field] = totals.get(field, 0) + value
    return totals


def format_stats(team: str) -> str:
    """One line per player: season totals, then the week-by-week trend."""
    lines = [f"Season stats for {team_name(team)} ({team}):"]
    for p in team_players(team):
        totals = ", ".join(f"{k}={v}" for k, v in season_totals(p).items())
        weekly = "; ".join(
            f"W{w.week}: " + ", ".join(f"{k}={getattr(w, k)}" for k in STAT_FIELDS if getattr(w, k) is not None)
            for w in p.weekly_stats
        )
        lines.append(f"- {p.name} ({p.position}, {p.id}) totals: {totals} | by week: {weekly}")
    return "\n".join(lines)


def format_injuries(team: str) -> str:
    names = {p.id: f"{p.name} ({p.position})" for p in team_players(team)}
    rows = [i for i in load_injuries() if i.player_id in names]
    if not rows:
        return f"Injury report for {team}: no players listed."
    lines = [f"Injury report for {team}:"]
    lines += [f"- {names[i.player_id]}: {i.designation}. {i.note} (updated {i.updated})" for i in rows]
    return "\n".join(lines)


def team_games(team: str) -> list[Game]:
    """Every bundled play-by-play file in which `team` played."""
    team_name(team)
    games = [load_game(f.name) for f in sorted(FIXTURES.glob("game-*.json"))]
    return [g for g in games if team in (g.home, g.away)]


def _format_play(play: Play) -> str:
    tags = [t for t, on in (("SCORE", play.scoring), ("TURNOVER", play.turnover), ("INJURY", play.injury)) if on]
    tag = f" [{', '.join(tags)}]" if tags else ""
    return (
        f"Q{play.quarter} {play.clock} {play.offense} ball, {play.down}&{play.distance} at {play.yard_line}: "
        f"{play.play_type} for {play.yards}. {play.description}{tag}"
    )


def format_plays(team: str, side: str = "all", quarter: int | None = None) -> str:
    """Play-by-play lines for `team`'s games.

    side: "offense" (team had the ball), "defense" (opponent had the ball) or "all".
    quarter: only that quarter, when given. Filtering here keeps tool output small.
    """
    if side not in ("offense", "defense", "all"):
        raise ValueError("side must be 'offense', 'defense' or 'all'")
    games = team_games(team)
    if not games:
        return f"No play-by-play film on file for {team}."
    lines: list[str] = []
    for g in games:
        lines.append(f"Game {g.id} (week {g.week}, {g.away} at {g.home}), final {g.final_score}:")
        for play in g.plays:
            if side == "offense" and play.offense != team:
                continue
            if side == "defense" and play.offense == team:
                continue
            if quarter is not None and play.quarter != quarter:
                continue
            lines.append("- " + _format_play(play))
    return "\n".join(lines)
