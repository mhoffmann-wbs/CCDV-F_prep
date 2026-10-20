"""Loads the bundled JSON data in data/. The files are read-only fixtures."""

import json
from functools import cache
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


@cache
def _load(name: str) -> Any:
    return json.loads((DATA_DIR / name).read_text(encoding="utf-8"))


def players() -> list[dict[str, Any]]:
    return _load("players.json")


def teams() -> dict[str, str]:
    """Team id -> team name."""
    return {t["id"]: t["name"] for t in _load("teams.json")}


def games() -> list[dict[str, Any]]:
    return _load("games.json")["games"]


def player(player_id: str) -> dict[str, Any]:
    for p in players():
        if p["id"] == player_id:
            return p
    raise KeyError(f"unknown player id: {player_id}")
