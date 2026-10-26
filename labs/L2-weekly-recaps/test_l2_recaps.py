import json

import pytest
from l2_recaps import (
    CUSTOM_ID,
    LEAGUE_CONTEXT,
    all_jobs,
    box_score,
    build_params,
    build_requests,
    foreign_players,
    ppr_points,
    system_blocks,
)

from gridiron.data import WeeklyStats, load_players

MODEL = "claude-haiku-5-5"


def test_twelve_jobs_with_unique_valid_custom_ids():
    requests = build_requests(MODEL)
    ids = [r["custom_id"] for r in requests]
    assert len(ids) == len(all_jobs()) == 12
    assert len(set(ids)) == len(ids)
    assert all(CUSTOM_ID.match(i) for i in ids)
    assert "por-w3" in ids


def test_shared_prefix_is_byte_identical_and_cached_with_the_1h_ttl():
    requests = build_requests(MODEL)
    systems = {json.dumps(r["params"]["system"], sort_keys=True) for r in requests}
    assert len(systems) == 1  # one prefix, so one cache entry serves every request
    (block,) = requests[0]["params"]["system"]
    assert block["cache_control"] == {"type": "ephemeral", "ttl": "1h"}


def test_per_request_content_comes_after_the_breakpoint():
    params = build_params("POR", 3, MODEL)
    assert "<box_score team=" not in json.dumps(params["system"])
    assert params["messages"][0]["content"].startswith('<box_score team="Portland Lumberjacks" week="3">')


def test_league_context_is_long_enough_to_cache_and_has_nothing_volatile():
    # 512 tokens is the minimum on current models; ~4 characters per token leaves a wide margin.
    assert len(LEAGUE_CONTEXT) > 4 * 1024
    for volatile in ("2026-", "today", "{", "}"):
        assert volatile not in LEAGUE_CONTEXT


def test_cache_modes():
    assert "cache_control" not in system_blocks("off")[0]
    assert system_blocks("5m")[0]["cache_control"] == {"type": "ephemeral"}
    with pytest.raises(ValueError):
        system_blocks("1d")


def test_no_sampling_parameters_and_effort_is_set():
    params = build_params("NSH", 1, MODEL)
    assert not {"temperature", "top_p", "top_k"} & params.keys()
    assert params["output_config"] == {"effort": "low"}


def test_box_score_lists_the_team_with_points():
    text = box_score("POR", 3)
    assert "Marcus Holloway (QB): 331 pass yds, 3 pass TD, 0 INT, 1 rush yds, 0 rush TD | 25.34 pts" in text
    assert text.count("\n") == 9  # open tag, 8 players, close tag
    with pytest.raises(ValueError):
        box_score("POR", 4)


def test_ppr_points():
    assert ppr_points(WeeklyStats(week=1, field_goals_made=2, extra_points_made=1)) == 7.0


def test_last_names_are_unique_so_the_check_is_unambiguous():
    last = [p.name.split()[-1] for p in load_players()]
    assert len(set(last)) == len(last)


def test_foreign_players_flags_other_teams_only():
    recap = "Holloway threw three scores while Brett Ashby added two. Kincaid would have helped."
    assert foreign_players(recap, "POR") == ["Darius Kincaid"]
    assert foreign_players("Holloway was sharp.", "POR") == []
