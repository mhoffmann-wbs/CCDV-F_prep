"""Command line: uv run python -m gridiron_stats <command> ..."""

import argparse

from . import data
from .fantasy import week_points
from .standings import standings


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="gridiron_stats")
    sub = parser.add_subparsers(dest="command", required=True)
    st = sub.add_parser("standings", help="league table")
    st.add_argument("--week", type=int, help="only count games up to this week")
    pts = sub.add_parser("points", help="PPR points for one player in one week")
    pts.add_argument("player_id")
    pts.add_argument("--week", type=int, required=True)
    args = parser.parse_args(argv)

    if args.command == "standings":
        names = data.teams()
        for rec in standings(args.week):
            print(
                f"{rec.team}  {names[rec.team]:<26} {rec.wins}-{rec.losses}-{rec.ties}"
                f"  pct {rec.win_pct:.3f}  diff {rec.point_diff:+d}"
            )
    elif args.command == "points":
        print(f"{args.player_id} week {args.week}: {week_points(args.player_id, args.week):.2f}")


if __name__ == "__main__":
    main()
