"""Standings from data/games.json (3 weeks, 4 teams, one tie)."""

from gridiron_stats import standings
from gridiron_stats.__main__ import main


def test_order_uses_point_diff_as_tiebreaker():
    # NSH and SAC are both 1-2; NSH has the better point differential.
    assert [r.team for r in standings()] == ["BAL", "POR", "NSH", "SAC"]


def test_tie_counts_as_half_a_win():
    por = next(r for r in standings() if r.team == "POR")
    assert (por.wins, por.losses, por.ties) == (1, 1, 1)
    assert por.win_pct == 0.5


def test_through_week():
    assert [r.team for r in standings(through_week=1)][:2] == ["SAC", "BAL"]


def test_cli_standings(capsys):
    main(["standings"])
    assert capsys.readouterr().out.splitlines()[0].startswith("BAL")
