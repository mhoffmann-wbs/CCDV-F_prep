"""PPR scoring. Expected values are worked out by hand from data/players.json."""

import pytest

from gridiron_stats import ppr_points, season_points
from gridiron_stats.fantasy import week_points


def test_receptions_score_one_point_each():
    # Full PPR: 5 catches for 0 yards is 5 points.
    assert ppr_points({"receptions": 5, "receiving_yds": 0}) == 5.0


def test_interceptions_cost_two_points():
    assert ppr_points({"interceptions": 2}) == -4.0


def test_unknown_keys_are_ignored():
    assert ppr_points({"week": 3, "tackles": 9}) == 0.0


def test_qb_week_1():
    # 208 pass yds (8.32) - 2 INT (-4) + 17 rush yds (1.7)
    assert week_points("POR-QB1", 1) == pytest.approx(6.02)


def test_rb_week_1_counts_catches():
    # 47 rush yds (4.7) + 4 rec (4) + 38 rec yds (3.8)
    assert week_points("POR-RB1", 1) == pytest.approx(12.5)


def test_rb_season_total():
    assert season_points("POR-RB1") == pytest.approx(53.2)


def test_kicker():
    assert week_points("POR-K1", 1) == pytest.approx(6.0)


def test_missing_week_scores_zero():
    assert week_points("POR-QB1", 17) == 0.0
