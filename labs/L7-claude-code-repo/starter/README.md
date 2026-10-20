# gridiron-stats

Fantasy points (full PPR: one point per reception) and standings for a small fictional football league.

```bash
uv run pytest
uv run python -m gridiron_stats standings
uv run python -m gridiron_stats points POR-RB1 --week 1
```

## Open issues

1. **Bug:** some running backs and receivers score too few points. Several tests in `tests/test_l7_fantasy.py` fail.
2. **Feature:** `top_performers(week, team=None, n=3)` in `gridiron_stats/fantasy.py` is a stub, and the CLI has no `top` command yet.

The JSON files in `data/` are fixtures. Don't edit them to make a test pass.
