# gridiron-stats

Fantasy points (full PPR) and standings for a small fictional football league. Pure Python, no dependencies.

## Commands

- Run tests: `uv run pytest` (one file: `uv run pytest tests/test_l7_fantasy.py`)
- Standings: `uv run python -m gridiron_stats standings [--week N]`
- One player's points: `uv run python -m gridiron_stats points POR-QB1 --week 3`
- Top performers: `uv run python -m gridiron_stats top --week 3 [--team POR] [-n 3]`

## Layout

- `gridiron_stats/fantasy.py`: scoring. Every weight lives in the `SCORING` dict.
- `gridiron_stats/standings.py`: W-L-T records, sorted by win pct, then point differential.
- `gridiron_stats/data.py`: the only module that reads `data/*.json`.
- `data/`: read-only fixtures. A PreToolUse hook blocks edits here, so fix code or tests, never the data.

## Conventions

- Any scoring change needs a test with the expected value worked out by hand in a comment.
- Python 3.11+, type hints on public functions, no new dependencies without asking.
- Run `uv run pytest` before saying a change is done.
