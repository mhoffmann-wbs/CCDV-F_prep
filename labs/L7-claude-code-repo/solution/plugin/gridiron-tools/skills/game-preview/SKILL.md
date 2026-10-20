---
name: game-preview
description: Write a short preview of a matchup in this fictional league from the bundled data (standings, records, top fantasy performers). Use when the user asks to preview a game or matchup, such as "preview POR at NSH".
argument-hint: "[away-team] [home-team] [week]"
arguments: [away, home, week]
allowed-tools: Bash(uv run python -m gridiron_stats *)
---

Write a game preview for **$away at $home** (week $week; if no week was given, use the latest week in the data).

## Gather the facts

Run these commands and use only their output. Don't invent stats, injuries or quotes.

1. `uv run python -m gridiron_stats standings`
2. `uv run python -m gridiron_stats top --week <week> --team $away -n 3`
3. `uv run python -m gridiron_stats top --week <week> --team $home -n 3`

If a team id isn't in the standings, stop and list the valid ids.

## Write the preview

Use exactly this shape, under 200 words:

```
## <Away team name> at <Home team name>
**Records:** <away W-L-T, point diff> vs <home W-L-T, point diff>
**Players to watch:** <two or three names with their PPR points from the last week>
**Storyline:** <two or three sentences grounded in the numbers above>
**Fantasy angle:** <one start or sit tip, with the number behind it>
```

End with the line: _All teams and players are fictional._
