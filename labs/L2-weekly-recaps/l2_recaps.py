"""L2 offline helpers: the shared league context, per-team box scores and batch requests.

Nothing here calls the API. The point of the design:
- One LEAGUE_CONTEXT, byte-identical in every request and marked with
  cache_control, so the shared prefix is written once and then read cheaply.
- Everything that differs per request (the box score, the ask) comes AFTER the
  cache breakpoint, in the user message.
- A custom_id per request, because batch results come back in any order.
"""

from __future__ import annotations

import re
from typing import Any

from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
from anthropic.types.messages.batch_create_params import Request

from gridiron.data import Player, WeeklyStats, load_players, load_teams

WEEKS = (1, 2, 3)
MAX_TOKENS = 4000  # recaps are short, but thinking counts toward max_tokens too

SCORING: dict[str, float] = {
    "passing_yds": 0.04,
    "passing_td": 4,
    "interceptions": -2,
    "rushing_yds": 0.1,
    "rushing_td": 6,
    "receptions": 1,
    "receiving_yds": 0.1,
    "receiving_td": 6,
    "field_goals_made": 3,
    "extra_points_made": 1,
}

STAT_LABELS = {
    "passing_yds": "pass yds",
    "passing_td": "pass TD",
    "interceptions": "INT",
    "rushing_yds": "rush yds",
    "rushing_td": "rush TD",
    "receptions": "rec",
    "receiving_yds": "rec yds",
    "receiving_td": "rec TD",
    "field_goals_made": "FG",
    "extra_points_made": "XP",
}

CACHE_MODES = ("1h", "5m", "off")
CUSTOM_ID = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")  # the format batch custom_ids must match


def ppr_points(line: WeeklyStats) -> float:
    stats = line.model_dump(exclude={"week"}, exclude_none=True)
    return round(float(sum(SCORING[k] * v for k, v in stats.items())), 2)


def _roster_lines() -> str:
    teams = {t.id: t.name for t in load_teams()}
    lines = []
    for team_id, name in teams.items():
        players = ", ".join(f"{p.name} ({p.position}, {p.id})" for p in load_players() if p.team == team_id)
        lines.append(f"- {name} ({team_id}): {players}")
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# The shared, cached prefix. It must be identical in every request: no dates,
# no request ids, no per-team content. It must also be longer than the model's
# minimum cacheable length (512 tokens on the current models), or caching
# silently does nothing.
# --------------------------------------------------------------------------- #

LEAGUE_CONTEXT = f"""\
You write the team recaps for "The Gridiron Weekly", the newsletter of a fictional \
four-team football league. Fans read one short recap per team per week on their phones, \
so every recap must be accurate, specific and quick to read.

<league>
Teams and players (name, position, player id):
{_roster_lines()}

Fantasy scoring is full PPR: 1 point per reception, 0.1 per rushing or receiving yard, \
0.04 per passing yard, 4 per passing touchdown, 6 per rushing or receiving touchdown, \
-2 per interception, 3 per field goal and 1 per extra point.
</league>

<style_guide>
- Write 90 to 130 words of plain prose. No headings, no bullet points, no emoji.
- Start with a headline on its own line, at most 10 words, then one paragraph.
- Name the team's top fantasy scorer for the week and give his points to one decimal.
- Mention at least two other players by name with one concrete stat each.
- If a player struggled (for example an interception or a quiet day for a starter), say \
so plainly but without mockery.
- Use only the numbers in the <box_score>. Never invent scores, opponents, quotes, \
injuries or plays: the box score does not contain them, and fans check every number.
- Only mention players from the team in the box score.
- Refer to players by full name on first mention and by last name after that.
- Round fantasy points to one decimal (25.34 becomes 25.3). Keep yards and catches as given.
- Write numbers under ten as words ("three touchdowns"), and 10 and above as digits.
- Prefer active verbs ("Vance caught six passes") over stat dumps ("Vance: 6 rec, 63 yds").
</style_guide>

<vocabulary>
Use these terms consistently, because the newsletter's readers range from new fans to \
league veterans:
- "touchdown" (not "TD", "score" is fine on second use); "interception" (not "pick" in \
the first sentence); "field goal" and "extra point" spelled out.
- "fantasy points" on first use in a recap, "points" after that.
- Positions: quarterback, running back, wide receiver (or "wideout"), tight end, kicker. \
Don't use the abbreviations QB, RB, WR, TE or K in prose.
- A player with more than 100 receiving or rushing yards had "a 100-yard day"; a \
quarterback with three or more passing touchdowns had "a three-touchdown day".
- A player with fewer than five fantasy points had "a quiet day", never "a bust".
</vocabulary>

<corrections>
Mistakes readers have written in about, which every recap must avoid:
- Crediting a passing touchdown to the receiver's fantasy total twice. The box score \
already splits it: the quarterback gets 4 points, the receiver 6.
- Calling a team's top scorer by the wrong position, for example a tight end "receiver".
- Mentioning a player from the opposing team. The box score lists only one team.
- Reporting a game result or a final score. Recaps cover individual performances only.
- Inventing a reason for a quiet day, such as an injury or the weather.
</corrections>

<example>
This example shows the format only. Its players and numbers are made up and must never \
appear in a real recap.

Kessler's three scores power a balanced attack

Quarterback Dan Kessler threw for 287 yards and three touchdowns, good for 25.5 fantasy \
points and the team's best line of the week. Running back Theo Marsh carried the load on \
the ground with 96 rushing yards, while tight end Abe Lund caught all six of his targets \
for 58 yards. Not everything clicked: wideout Ray Ortiz managed just two catches for 19 \
yards after a 100-yard outing the week before. Kicker Sam Hale was perfect on two field \
goals and three extra points, adding nine points in a game where every possession counted.
</example>"""

RECAP_REQUEST = (
    "Write this week's recap for the team in <box_score>, following the style guide. "
    "Return only the headline and the paragraph."
)


def box_score(team: str, week: int) -> str:
    """One team's stat lines for one week, with fantasy points, inside <box_score> tags."""
    teams = {t.id: t.name for t in load_teams()}
    if team not in teams:
        raise ValueError(f"unknown team {team!r}")
    if week not in WEEKS:
        raise ValueError(f"week must be one of {WEEKS}, got {week}")
    lines = []
    for p in (p for p in load_players() if p.team == team):
        line = next(w for w in p.weekly_stats if w.week == week)
        stats = line.model_dump(exclude={"week"}, exclude_none=True)
        detail = ", ".join(f"{v} {STAT_LABELS[k]}" for k, v in stats.items())
        lines.append(f"{p.name} ({p.position}): {detail} | {ppr_points(line)} pts")
    return f'<box_score team="{teams[team]}" week="{week}">\n' + "\n".join(lines) + "\n</box_score>"


def custom_id(team: str, week: int) -> str:
    return f"{team.lower()}-w{week}"


def all_jobs() -> list[tuple[str, int]]:
    """Every (team, week) recap the newsletter needs: 4 teams x 3 weeks."""
    return [(t.id, w) for w in WEEKS for t in load_teams()]


def system_blocks(cache: str = "1h") -> list[dict[str, Any]]:
    """The shared prefix, with a cache breakpoint on its last block.

    cache="1h" for batches (they can take longer than 5 minutes), "5m" (the default
    TTL) for realtime calls that follow each other closely, "off" for a baseline.
    """
    if cache not in CACHE_MODES:
        raise ValueError(f"cache must be one of {CACHE_MODES}")
    block: dict[str, Any] = {"type": "text", "text": LEAGUE_CONTEXT}
    if cache == "1h":
        block["cache_control"] = {"type": "ephemeral", "ttl": "1h"}
    elif cache == "5m":
        block["cache_control"] = {"type": "ephemeral"}
    return [block]


def build_params(team: str, week: int, model: str, *, cache: str = "1h") -> dict[str, Any]:
    """Messages API parameters for one recap. The same dict works for a realtime call
    (client.messages.create(**params)) and as a batch request's params."""
    return {
        "model": model,
        "max_tokens": MAX_TOKENS,
        "output_config": {"effort": "low"},
        "system": system_blocks(cache),
        "messages": [{"role": "user", "content": f"{box_score(team, week)}\n\n{RECAP_REQUEST}"}],
    }


def build_requests(model: str, jobs: list[tuple[str, int]] | None = None) -> list[Request]:
    return [
        Request(custom_id=custom_id(team, week), params=MessageCreateParamsNonStreaming(**build_params(team, week, model)))
        for team, week in (jobs or all_jobs())
    ]


def foreign_players(recap: str, team: str) -> list[str]:
    """Players from OTHER teams named in a recap. A cheap code check for one style-guide rule."""
    return sorted(p.name for p in load_players() if p.team != team and _mentions(recap, p))


def _mentions(text: str, player: Player) -> bool:
    return player.name in text or re.search(rf"\b{re.escape(player.name.split()[-1])}\b", text) is not None
