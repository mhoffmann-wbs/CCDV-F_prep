"""Full-PPR fantasy scoring: one point per reception.

All scoring weights live in SCORING. Change them there, never inline.
"""

from typing import Any

from . import data

SCORING: dict[str, float] = {
    "passing_yds": 0.04,  # 1 point per 25 yards
    "passing_td": 4,
    "interceptions": -2,
    "rushing_yds": 0.1,  # 1 point per 10 yards
    "rushing_td": 6,
    "receptions": 1,  # full PPR
    "receiving_yds": 0.1,
    "receiving_td": 6,
    "field_goals_made": 3,
    "extra_points_made": 1,
}


def ppr_points(stat_line: dict[str, Any]) -> float:
    """Fantasy points for one weekly stat line, rounded to 2 decimals.

    Keys that aren't in SCORING (such as "week") are ignored.
    """
    total = sum(SCORING[key] * value for key, value in stat_line.items() if key in SCORING)
    return round(float(total), 2)


def week_points(player_id: str, week: int) -> float:
    for line in data.player(player_id)["weekly_stats"]:
        if line["week"] == week:
            return ppr_points(line)
    return 0.0


def season_points(player_id: str) -> float:
    return round(sum(ppr_points(line) for line in data.player(player_id)["weekly_stats"]), 2)


def top_performers(week: int, team: str | None = None, n: int = 3) -> list[tuple[str, str, float]]:
    """The n highest-scoring players in a week, optionally for one team.

    Returns (player_id, name, points) tuples, highest first. Ties keep data order.
    """
    if n < 1:
        raise ValueError("n must be at least 1")
    rows = [
        (p["id"], p["name"], week_points(p["id"], week))
        for p in data.players()
        if team is None or p["team"] == team
    ]
    rows.sort(key=lambda row: row[2], reverse=True)
    return rows[:n]
