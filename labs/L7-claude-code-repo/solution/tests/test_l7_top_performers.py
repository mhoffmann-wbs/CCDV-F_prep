"""The feature added in the lab: top_performers() and the `top` command."""

import pytest

from gridiron_stats import top_performers
from gridiron_stats.__main__ import main


def test_top_three_week_3():
    assert [pid for pid, _, _ in top_performers(3)] == ["POR-TE1", "POR-QB1", "POR-WR1"]


def test_filter_by_team():
    rows = top_performers(3, team="NSH", n=2)
    assert [pid for pid, _, _ in rows] == ["NSH-QB1", "NSH-WR1"]
    assert rows[0][2] == pytest.approx(17.38)


def test_sorted_highest_first():
    points = [pts for _, _, pts in top_performers(2, n=10)]
    assert points == sorted(points, reverse=True)


def test_n_must_be_positive():
    with pytest.raises(ValueError):
        top_performers(1, n=0)


def test_cli_top(capsys):
    main(["top", "--week", "3", "--team", "POR", "-n", "1"])
    assert "POR-TE1" in capsys.readouterr().out
