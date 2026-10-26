"""L9 evals: the pick'em cases, the output schema, code graders, the LLM judge and its calibration.

Nothing here calls the API. Grade in this order:
  1. code graders: cheap, exact, run on every output; they catch what rules can express
  2. an LLM judge: for what rules can't express (is every claim backed by the data?)
  3. humans: label a sample once, and use the labels to calibrate the judge
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from gridiron.data import load_injuries, load_players, load_teams

LAB_DIR = Path(__file__).resolve().parent
RECORDED = LAB_DIR / "recorded_picks.json"
sys.path.insert(0, str(LAB_DIR.parent / "L5-league-mcp"))
from l5_data import SCHEDULE, injury_text, stats_text  # noqa: E402

# --------------------------------------------------------------------------- #
# Cases: one per scheduled game, with the data Claude may use and nothing else.
# --------------------------------------------------------------------------- #


class Case(BaseModel):
    id: str
    week: int
    away: str
    home: str
    data: str


def build_cases() -> list[Case]:
    names = {t.id: t.name for t in load_teams()}
    players = load_players()
    injured = {i.player_id for i in load_injuries()}
    cases = []
    for week, away, home in SCHEDULE:
        ids = [p.id for p in players if p.team in (away, home)]
        hurt = [pid for pid in ids if pid in injured]
        data = (
            f"<matchup>Week {week}: {names[away]} ({away}) at {names[home]} ({home})</matchup>\n"
            f"<season_stats>\n{stats_text(ids)}\n</season_stats>\n"
            f"<injuries>\n{injury_text(hurt) if hurt else 'none'}\n</injuries>"
        )
        cases.append(Case(id=f"w{week}-{away.lower()}-{home.lower()}", week=week, away=away, home=home, data=data))
    return cases


# --------------------------------------------------------------------------- #
# The output schema. Ranges live in descriptions and in the code graders,
# because structured outputs don't enforce minimum/maximum or list lengths.
# --------------------------------------------------------------------------- #


class Factor(BaseModel):
    player_id: str = Field(description='Exact player id from the data, e.g. "POR-TE1".')
    claim: str = Field(description="One sentence about this player, using only numbers from the data.")


class Pick(BaseModel):
    winner: str = Field(description="Team abbreviation of the predicted winner: the away or the home team.")
    confidence: int = Field(description="50 (coin flip) to 100 (certain).")
    key_factors: list[Factor] = Field(description="Two or three players who decide the game.")
    rationale: str = Field(description="Two sentences that explain the pick using only the data.")


PICK_SYSTEM = """\
You make pick'em predictions for a fictional football league. Use only the data in the \
user message: season stats (full-PPR fantasy points per week) and the injury report. \
Don't invent records, streaks, head-to-head history, weather, quotes or anything else the \
data doesn't contain. A player ruled Out will not play; mention him only as a missing piece."""

PICK_REQUEST = "Pick the winner of this game."


def pick_messages(case: Case) -> list[dict[str, Any]]:
    return [{"role": "user", "content": f"{case.data}\n\n{PICK_REQUEST}"}]


# --------------------------------------------------------------------------- #
# Code graders: exact checks that need no model.
# --------------------------------------------------------------------------- #

NUMBER = re.compile(r"(?<![\w.-])\d+(?:\.\d+)?(?![\w-])")


def _allowed_numbers(player_id: str) -> set[float]:
    """Every number in the player's data (weekly points, raw stats, average), plus week numbers."""
    return {float(n) for n in NUMBER.findall(stats_text([player_id], "full"))} | {1.0, 2.0, 3.0}


def _grounded(number: float, allowed: set[float]) -> bool:
    # Rounding is fine (23.83 -> 23.8 or 24); anything else is an invented number.
    return any(abs(number - a) < 0.051 or (number == round(a) and number.is_integer()) for a in allowed)


def grade_code(pick: Pick, case: Case) -> list[str]:
    problems = []
    players = {p.id: p for p in load_players()}
    designations = {i.player_id: i.designation for i in load_injuries()}
    if pick.winner not in (case.away, case.home):
        problems.append(f"winner {pick.winner!r} is not {case.away} or {case.home}")
    if not 50 <= pick.confidence <= 100:
        problems.append(f"confidence {pick.confidence} is outside 50-100")
    if not 2 <= len(pick.key_factors) <= 3:
        problems.append(f"{len(pick.key_factors)} key factors, expected 2-3")
    for f in pick.key_factors:
        p = players.get(f.player_id)
        if p is None:
            problems.append(f"unknown player id {f.player_id!r}")
            continue
        if p.team not in (case.away, case.home):
            problems.append(f"{f.player_id} doesn't play in this game")
            continue
        allowed = _allowed_numbers(f.player_id)
        for raw in NUMBER.findall(f.claim):
            if not _grounded(float(raw), allowed):
                problems.append(f"{f.player_id}: {raw} is not in his stats")
        if designations.get(f.player_id) == "Out" and not re.search(r"\bout\b", f.claim, re.IGNORECASE):
            problems.append(f"cites {f.player_id} (Out) as if he will play")
    return problems


# --------------------------------------------------------------------------- #
# The LLM judge: one question, a rubric, reasoning before the verdict.
# --------------------------------------------------------------------------- #


class JudgeVerdict(BaseModel):
    reasoning: str = Field(description="Check each claim in the pick against the data, one by one.")
    unsupported_claims: list[str] = Field(description="Claims the data doesn't support; empty if none.")
    grounded: bool = Field(description="True only if every claim in the pick is supported by the data.")


JUDGE_SYSTEM = """\
You grade pick'em predictions for grounding. You decide one thing: is every claim in the \
pick supported by the data the predictor was given?

A claim is supported if the data states it or it follows directly from the numbers, \
including rounding and simple comparisons ("averages about 24 points", "scored more in \
week 3 than in week 1"). A claim is unsupported if it relies on anything the data doesn't \
contain: records, streaks, head-to-head history, weather, venue, quotes, coaching, or a \
player's role or health beyond the injury report. Whether the pick itself is wise doesn't \
matter. Check every claim, then give the verdict."""


def judge_messages(case: Case, pick: Pick) -> list[dict[str, Any]]:
    return [
        {
            "role": "user",
            "content": f"<data>\n{case.data}\n</data>\n\n<pick>\n{pick.model_dump_json(indent=2)}\n</pick>\n\n"
            "Is every claim in the pick supported by the data?",
        }
    ]


# --------------------------------------------------------------------------- #
# Calibration: does the judge agree with humans, and how does it fail?
# --------------------------------------------------------------------------- #


class Recorded(BaseModel):
    id: str
    case: str
    pick: Pick
    human_grounded: bool
    note: str


def load_recorded(path: Path = RECORDED) -> list[Recorded]:
    return [Recorded.model_validate(r) for r in json.loads(path.read_text())]


def calibration(human: list[bool], judge: list[bool]) -> dict[str, float | int]:
    """Agreement plus the two error rates. A false pass (judge says grounded, a human
    said not) lets bad output through, so it's the number to drive down first."""
    pairs = list(zip(human, judge, strict=True))
    bad = [j for h, j in pairs if not h]
    good = [j for h, j in pairs if h]
    return {
        "n": len(pairs),
        "agreement": sum(h == j for h, j in pairs) / len(pairs),
        "false_pass_rate": sum(bad) / len(bad) if bad else 0.0,
        "false_fail_rate": sum(not j for j in good) / len(good) if good else 0.0,
    }
