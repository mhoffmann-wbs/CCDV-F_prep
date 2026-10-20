"""Typed access to the fictional league fixtures in labs/fixtures/.

Every lab reads data through here so the shapes are validated once.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, TypeAdapter

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"

Position = Literal["QB", "RB", "WR", "TE", "K"]


class Team(BaseModel):
    id: str
    name: str
    conference: Literal["East", "West"]


class WeeklyStats(BaseModel):
    week: int
    passing_yds: int | None = None
    passing_td: int | None = None
    interceptions: int | None = None
    rushing_yds: int | None = None
    rushing_td: int | None = None
    receptions: int | None = None
    receiving_yds: int | None = None
    receiving_td: int | None = None
    field_goals_made: int | None = None
    extra_points_made: int | None = None


class Player(BaseModel):
    id: str
    name: str
    team: str
    position: Position
    weekly_stats: list[WeeklyStats]


class Injury(BaseModel):
    player_id: str
    designation: Literal["Out", "Doubtful", "Questionable", "Full"]
    note: str
    updated: str


class Play(BaseModel):
    quarter: int
    clock: str
    offense: str
    down: int
    distance: int
    yard_line: str
    play_type: Literal["run", "pass", "field_goal", "punt"]
    yards: int
    description: str
    player_ids: list[str]
    score_after: dict[str, int]
    scoring: bool = False
    turnover: bool = False
    injury: bool = False


class Game(BaseModel):
    id: str
    week: int
    date: str
    home: str
    away: str
    venue: str
    final_score: dict[str, int]
    note: str
    plays: list[Play]


def _load(file: str, adapter: TypeAdapter):
    return adapter.validate_python(json.loads((FIXTURES / file).read_text()))


def load_teams() -> list[Team]:
    return _load("teams.json", TypeAdapter(list[Team]))


def load_players() -> list[Player]:
    return _load("players.json", TypeAdapter(list[Player]))


def load_injuries() -> list[Injury]:
    return _load("injuries.json", TypeAdapter(list[Injury]))


def load_game(file: str = "game-week3-por-nsh.json") -> Game:
    return _load(file, TypeAdapter(Game))
