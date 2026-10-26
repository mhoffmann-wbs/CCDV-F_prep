"""L4 offline domain: your fantasy roster, PPR scoring and the lineup rules.

Nothing here calls the API. The tools in l4_tools.py are thin wrappers over
these functions, so every rule is covered by test_l4_league.py without a key.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from gridiron.data import Injury, Player, WeeklyStats, load_injuries, load_players

LAB_DIR = Path(__file__).resolve().parent
OUT_DIR = LAB_DIR / "out"

UPCOMING_WEEK = 4

# Full-PPR scoring, the same weights as the L7 repo. Change them here, never inline.
SCORING: dict[str, float] = {
    "passing_yds": 0.04,  # 1 point per 25 yards
    "passing_td": 4,
    "interceptions": -2,
    "rushing_yds": 0.1,  # 1 point per 10 yards
    "rushing_td": 6,
    "receptions": 1,
    "receiving_yds": 0.1,
    "receiving_td": 6,
    "field_goals_made": 3,
    "extra_points_made": 1,
}

# Starting slots and the positions each one accepts. FLEX takes any RB, WR or TE.
SLOTS: dict[str, tuple[str, ...]] = {
    "QB": ("QB",),
    "RB1": ("RB",),
    "RB2": ("RB",),
    "WR1": ("WR",),
    "WR2": ("WR",),
    "TE": ("TE",),
    "FLEX": ("RB", "WR", "TE"),
    "K": ("K",),
}

# Your fantasy team "Gridiron Gurus": 15 players drawn from all four league teams.
# Several carry an injury designation, so the lineup is a real decision.
MY_ROSTER: tuple[str, ...] = (
    "POR-QB1", "SAC-QB1",
    "POR-RB1", "NSH-RB2", "BAL-RB2", "SAC-RB2",
    "NSH-WR1", "BAL-WR1", "POR-WR3", "SAC-WR1", "NSH-WR3",
    "BAL-TE1", "POR-TE1",
    "NSH-K1", "SAC-K1",
)

# Designations a starter may not carry. Enforced in code, not only asked for in the prompt.
BLOCKED = ("Out",)


class UnknownPlayerError(ValueError):
    pass


def _players() -> dict[str, Player]:
    return {p.id: p for p in load_players()}


def _injuries() -> dict[str, Injury]:
    return {i.player_id: i for i in load_injuries()}


def ppr_points(line: WeeklyStats) -> float:
    stats = line.model_dump(exclude={"week"}, exclude_none=True)
    return round(float(sum(SCORING[k] * v for k, v in stats.items())), 2)


def _lookup(player_ids: list[str]) -> list[Player]:
    players = _players()
    unknown = [pid for pid in player_ids if pid not in players]
    if unknown:
        raise UnknownPlayerError(
            f"Unknown player id(s): {', '.join(unknown)}. Ids look like POR-QB1; "
            "call get_roster to see valid ids."
        )
    return [players[pid] for pid in player_ids]


# --------------------------------------------------------------------------- #
# Read-only views. Each returns compact text: the tool output IS context, so
# it carries only what the decision needs (tool-output pruning at the source).
# --------------------------------------------------------------------------- #


def roster_text() -> str:
    players = _players()
    injuries = _injuries()
    lines = [f"Gridiron Gurus roster ({len(MY_ROSTER)} players). Starting slots: {', '.join(SLOTS)}."]
    for pid in MY_ROSTER:
        p = players[pid]
        tag = f" [{injuries[pid].designation}]" if pid in injuries else ""
        lines.append(f"{pid} | {p.name} | {p.position} | {p.team}{tag}")
    return "\n".join(lines)


def stats_text(player_ids: list[str], detail: str = "summary") -> str:
    """Fantasy points per week (summary) or the raw stat lines too (full)."""
    if detail not in ("summary", "full"):
        raise ValueError('detail must be "summary" or "full"')
    lines = []
    for p in _lookup(player_ids):
        points = [ppr_points(w) for w in p.weekly_stats]
        avg = round(sum(points) / len(points), 2) if points else 0.0
        weeks = ", ".join(f"W{w.week} {pts}" for w, pts in zip(p.weekly_stats, points))
        lines.append(f"{p.id} | {p.name} | {p.position} | PPR {weeks} | avg {avg}")
        if detail == "full":
            for w in p.weekly_stats:
                raw = w.model_dump(exclude={"week"}, exclude_none=True)
                lines.append(f"    W{w.week}: {json.dumps(raw)}")
    return "\n".join(lines)


def injury_text(player_ids: list[str]) -> str:
    injuries = _injuries()
    lines = []
    for p in _lookup(player_ids):
        i = injuries.get(p.id)
        if i is None:
            lines.append(f"{p.id} | {p.name} | no injury designation")
        else:
            lines.append(f"{p.id} | {p.name} | {i.designation} | {i.note} (updated {i.updated})")
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# The write path: validate first, then (after approval) save.
# --------------------------------------------------------------------------- #


def validate_lineup(week: int, lineup: dict[str, str]) -> list[str]:
    """Check a lineup against the rules. Returns problems (empty = valid).

    A strict tool schema guarantees the shape (every slot present, all strings).
    Only code can check the facts: on the roster, right position, no duplicates,
    nobody ruled Out.
    """
    problems: list[str] = []
    players = _players()
    injuries = _injuries()

    if week != UPCOMING_WEEK:
        problems.append(f"week must be {UPCOMING_WEEK} (the upcoming week), got {week}")
    missing = [s for s in SLOTS if s not in lineup]
    if missing:
        problems.append(f"missing slot(s): {', '.join(missing)}")
    extra = [s for s in lineup if s not in SLOTS]
    if extra:
        problems.append(f"unknown slot(s): {', '.join(extra)}")

    seen: dict[str, str] = {}
    for slot, pid in lineup.items():
        if slot not in SLOTS:
            continue
        if pid in seen:
            problems.append(f"{pid} is in both {seen[pid]} and {slot}")
            continue
        seen[pid] = slot
        if pid not in MY_ROSTER:
            problems.append(f"{slot}: {pid} is not on your roster")
            continue
        position = players[pid].position
        if position not in SLOTS[slot]:
            problems.append(f"{slot}: {pid} is a {position}; {slot} takes {'/'.join(SLOTS[slot])}")
        injury = injuries.get(pid)
        if injury and injury.designation in BLOCKED:
            problems.append(f"{slot}: {pid} is ruled {injury.designation} ({injury.note})")
    return problems


def format_lineup(lineup: dict[str, str]) -> str:
    players = _players()
    return "\n".join(f"  {slot:<4} {pid:<8} {players[pid].name}" for slot, pid in lineup.items() if pid in players)


@dataclass
class LineupStore:
    """Where an approved lineup is saved. Tests point `path` at a temp dir."""

    path: Path = field(default_factory=lambda: OUT_DIR / f"lineup-week{UPCOMING_WEEK}.json")

    def save(self, week: int, lineup: dict[str, str], rationale: str) -> Path:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps({"week": week, "lineup": lineup, "rationale": rationale}, indent=2) + "\n")
        return self.path

    def load(self) -> dict | None:
        return json.loads(self.path.read_text()) if self.path.exists() else None
