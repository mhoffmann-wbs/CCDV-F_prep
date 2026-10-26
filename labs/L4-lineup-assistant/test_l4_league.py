import pytest
from l4_league import (
    MY_ROSTER,
    SLOTS,
    LineupStore,
    UnknownPlayerError,
    injury_text,
    ppr_points,
    roster_text,
    stats_text,
    validate_lineup,
)

from gridiron.data import WeeklyStats, load_players

GOOD = {
    "QB": "POR-QB1",
    "RB1": "NSH-RB2",
    "RB2": "BAL-RB2",
    "WR1": "BAL-WR1",
    "WR2": "POR-WR3",
    "TE": "POR-TE1",
    "FLEX": "SAC-RB2",
    "K": "NSH-K1",
}


def test_roster_ids_exist_and_fill_every_slot():
    players = {p.id: p for p in load_players()}
    assert all(pid in players for pid in MY_ROSTER)
    assert len(set(MY_ROSTER)) == len(MY_ROSTER)
    assert set(GOOD) == set(SLOTS)


def test_ppr_scoring_matches_the_league_rules():
    line = WeeklyStats(week=3, passing_yds=331, passing_td=3, interceptions=0, rushing_yds=1, rushing_td=0)
    assert ppr_points(line) == 25.34  # 13.24 + 12 + 0.1


def test_roster_flags_injuries():
    text = roster_text()
    assert "NSH-WR1 | Darius Kincaid | WR | NSH [Out]" in text
    assert "SAC-QB1" in text and "[Doubtful]" in text


def test_summary_stats_are_one_line_per_player_and_full_adds_raw_lines():
    summary = stats_text(["POR-QB1", "NSH-K1"])
    assert summary.count("\n") == 1
    assert "W3 25.34" in summary and "avg" in summary
    full = stats_text(["POR-QB1"], "full")
    assert len(full) > len(stats_text(["POR-QB1"])) and '"passing_yds": 331' in full


def test_unknown_ids_raise_a_message_claude_can_act_on():
    with pytest.raises(UnknownPlayerError, match="POR-QB9.*get_roster"):
        stats_text(["POR-QB1", "POR-QB9"])
    with pytest.raises(ValueError):
        stats_text(["POR-QB1"], "everything")


def test_injury_text_covers_designated_and_healthy_players():
    text = injury_text(["POR-RB1", "POR-QB1"])
    assert "POR-RB1 | Devin Brightwater | Questionable | Hamstring" in text
    assert "POR-QB1 | Marcus Holloway | no injury designation" in text


def test_good_lineup_validates():
    assert validate_lineup(4, GOOD) == []


def test_bad_lineup_lists_every_problem():
    bad = dict(GOOD, QB="POR-RB1", WR1="NSH-WR1", WR2="BAL-WR2", FLEX="NSH-RB2")
    assert validate_lineup(5, bad) == [
        "week must be 4 (the upcoming week), got 5",
        "QB: POR-RB1 is a RB; QB takes QB",
        "WR1: NSH-WR1 is ruled Out (High ankle sprain; expected to miss 2-3 weeks.)",
        "WR2: BAL-WR2 is not on your roster",
        "NSH-RB2 is in both RB1 and FLEX",
    ]


def test_missing_and_unknown_slots_are_reported():
    lineup = {k: v for k, v in GOOD.items() if k != "K"} | {"DST": "BAL-K1"}
    problems = validate_lineup(4, lineup)
    assert "missing slot(s): K" in problems and "unknown slot(s): DST" in problems


def test_store_round_trips(tmp_path):
    store = LineupStore(tmp_path / "lineup.json")
    assert store.load() is None
    store.save(4, GOOD, "Best healthy players.")
    assert store.load() == {"week": 4, "lineup": GOOD, "rationale": "Best healthy players."}
