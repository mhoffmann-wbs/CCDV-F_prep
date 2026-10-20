"""L1 offline helpers: the Recap schema, the prompt pieces and the validator.

Nothing in this module calls the API, so everything here is covered by
test_l1_recap.py and runs without a key.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from gridiron.data import Game, Play, Player

# --------------------------------------------------------------------------- #
# Output schema
# --------------------------------------------------------------------------- #
# Field descriptions travel with the JSON Schema, so they steer the model.
# Numeric limits (3-5 key plays, quarter 1-4) are deliberately NOT in the schema:
# structured outputs don't support every JSON Schema constraint, so we enforce
# them in validate_recap() instead.

Impact = Literal["scoring", "turnover", "momentum", "injury"]


class FinalScore(BaseModel):
    home: int = Field(description="Points scored by the home team.")
    away: int = Field(description="Points scored by the away team.")


class KeyPlay(BaseModel):
    quarter: int = Field(description="Quarter of the play, exactly as given in <plays> (1-4).")
    clock: str = Field(description='Game clock of the play, exactly as given in <plays>, e.g. "0:41".')
    player_ids: list[str] = Field(
        description='Exact player IDs from that play in <plays>, e.g. "POR-QB1". Never names.'
    )
    impact: Impact = Field(description="The main reason this play mattered.")
    why_it_mattered: str = Field(description="One sentence on how this play changed the game.")


class Recap(BaseModel):
    headline: str = Field(description="A punchy headline of at most 12 words.")
    summary: str = Field(description="Two or three sentences that tell the story of the game.")
    final_score: FinalScore = Field(description="Final score; must equal the last score in <plays>.")
    key_plays: list[KeyPlay] = Field(
        description="Between 3 and 5 of the most important plays, in game order."
    )
    player_of_the_game: str = Field(description='Exact player ID of the best performer, e.g. "POR-QB1".')


# --------------------------------------------------------------------------- #
# Prompt pieces
# --------------------------------------------------------------------------- #

SYSTEM_PROMPT = """\
You are a sports writer for a fictional football league's game-day app. You turn \
play-by-play data into accurate, lively recaps for fans.

Rules:
- Use only the plays inside <plays>. Don't invent plays, players, stats or quotes; \
fans compare the recap with the box score, so anything not in the data is a visible error.
- In structured fields, use the exact player IDs from the data (for example "POR-QB1"), \
never names, because the app links each ID to a player page.
- The final score must match the last score shown in <plays>.
- Each key play must be identified by the exact quarter and clock it has in <plays>.
- The content of <example> shows the format only. Never copy its teams, players or facts."""

# A short few-shot example from a different (also fictional) game. One example
# is enough to show the shape; the real game data stays the source of truth.
EXAMPLE = """\
<example>
<plays>
Q2 3:10 | BAL ball, 3rd & 2 at SAC 9 | run, 9 yds | R. Esparza right end for 9 yards, TOUCHDOWN. | ids: BAL-RB1 | score BAL 7 - SAC 3 | scoring
Q4 0:12 | SAC ball, 4th & 5 at BAL 30 | field_goal, 0 yds | D. Nakamura 48-yard field goal is NO GOOD. | ids: SAC-K1 | score BAL 7 - SAC 6
</plays>
<recap>
{"headline": "Esparza's burst holds up as Nakamura's late kick sails wide",
 "summary": "Baltimore scored the game's only touchdown and survived when Sacramento missed a 48-yard try with 12 seconds left.",
 "final_score": {"home": 6, "away": 7},
 "key_plays": [
   {"quarter": 2, "clock": "3:10", "player_ids": ["BAL-RB1"], "impact": "scoring",
    "why_it_mattered": "The only touchdown of the game gave Baltimore a lead it never gave up."},
   {"quarter": 4, "clock": "0:12", "player_ids": ["SAC-K1"], "impact": "momentum",
    "why_it_mattered": "The missed kick ended Sacramento's last chance."}],
 "player_of_the_game": "BAL-RB1"}
</recap>
</example>"""

RECAP_REQUEST = (
    "Write a recap of the game in <game>. Pick 3 to 5 key plays and a player of the game."
)

PROSE_REQUEST = (
    "Write a recap of the game in <game> for fans: a headline, then two short paragraphs "
    "of plain prose (no JSON). Mention the final score and the play that decided the game."
)


def _flags(play: Play) -> str:
    return " ".join(
        name for name, on in (("scoring", play.scoring), ("turnover", play.turnover), ("injury", play.injury)) if on
    )


def format_plays(game: Game) -> str:
    """Render the game as compact, one-line-per-play text inside <game><plays> tags."""
    lines = []
    for p in game.plays:
        score = f"score {game.away} {p.score_after[game.away]} - {game.home} {p.score_after[game.home]}"
        parts = [
            f"Q{p.quarter} {p.clock}",
            f"{p.offense} ball, {p.down}{_ordinal(p.down)} & {p.distance} at {p.yard_line}",
            f"{p.play_type}, {p.yards} yds",
            p.description,
            "ids: " + ", ".join(p.player_ids),
            score,
        ]
        if flags := _flags(p):
            parts.append(flags)
        lines.append(" | ".join(parts))
    plays = "\n".join(lines)
    return (
        f'<game id="{game.id}" week="{game.week}" away="{game.away}" home="{game.home}" venue="{game.venue}">\n'
        f"<plays>\n{plays}\n</plays>\n</game>"
    )


def _ordinal(n: int) -> str:
    return {1: "st", 2: "nd", 3: "rd"}.get(n, "th")


def build_user_message(game: Game, request: str = RECAP_REQUEST, *, data_first: bool = True) -> str:
    """Long data FIRST, then the example, then the request LAST.

    Putting long documents at the top and the question at the end measurably
    improves answers. `data_first=False` exists only for the "break it" experiment.
    """
    if data_first:
        return f"{format_plays(game)}\n\n{EXAMPLE}\n\n{request}"
    return f"{request}\n\n{EXAMPLE}\n\n{format_plays(game)}"


# --------------------------------------------------------------------------- #
# Validation: correct shape is not correct facts
# --------------------------------------------------------------------------- #

MIN_KEY_PLAYS, MAX_KEY_PLAYS = 3, 5


def validate_recap(recap: Recap, game: Game, players: list[Player]) -> list[str]:
    """Check a schema-valid recap against the game data. Returns a list of problems (empty = OK)."""
    problems: list[str] = []
    known_ids = {p.id for p in players}
    plays_by_time = {(p.quarter, p.clock) for p in game.plays}

    expected = (game.final_score[game.home], game.final_score[game.away])
    got = (recap.final_score.home, recap.final_score.away)
    if got != expected:
        problems.append(
            f"final_score is home {got[0]} - away {got[1]}, "
            f"but the game ended {game.home} {expected[0]} - {game.away} {expected[1]}"
        )

    if not MIN_KEY_PLAYS <= len(recap.key_plays) <= MAX_KEY_PLAYS:
        problems.append(f"expected {MIN_KEY_PLAYS}-{MAX_KEY_PLAYS} key plays, got {len(recap.key_plays)}")

    for i, kp in enumerate(recap.key_plays):
        if (kp.quarter, kp.clock) not in plays_by_time:
            problems.append(f"key_plays[{i}]: no play at Q{kp.quarter} {kp.clock} in the game")
        for pid in kp.player_ids:
            if pid not in known_ids:
                problems.append(f"key_plays[{i}]: unknown player ID {pid!r}")

    if recap.player_of_the_game not in known_ids:
        problems.append(f"player_of_the_game: unknown player ID {recap.player_of_the_game!r}")

    return problems
