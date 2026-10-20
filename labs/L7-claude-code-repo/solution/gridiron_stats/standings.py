"""Team standings from the results in data/games.json."""

from dataclasses import dataclass

from . import data


@dataclass
class TeamRecord:
    team: str
    wins: int = 0
    losses: int = 0
    ties: int = 0
    points_for: int = 0
    points_against: int = 0

    @property
    def games(self) -> int:
        return self.wins + self.losses + self.ties

    @property
    def win_pct(self) -> float:
        """NFL style: a tie counts as half a win."""
        return 0.0 if self.games == 0 else round((self.wins + 0.5 * self.ties) / self.games, 3)

    @property
    def point_diff(self) -> int:
        return self.points_for - self.points_against


def standings(through_week: int | None = None) -> list[TeamRecord]:
    """Records for every team, best first: win pct, then point differential."""
    records = {team: TeamRecord(team) for team in data.teams()}
    for game in data.games():
        if through_week is not None and game["week"] > through_week:
            continue
        home, away = game["home"], game["away"]
        home_pts, away_pts = game["score"][home], game["score"][away]
        for team, scored, allowed in ((home, home_pts, away_pts), (away, away_pts, home_pts)):
            rec = records[team]
            rec.points_for += scored
            rec.points_against += allowed
            if scored > allowed:
                rec.wins += 1
            elif scored < allowed:
                rec.losses += 1
            else:
                rec.ties += 1
    return sorted(records.values(), key=lambda r: (r.win_pct, r.point_diff), reverse=True)
