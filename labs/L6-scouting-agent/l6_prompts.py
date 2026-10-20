"""L6 prompts for both versions. Pure string builders, so they can be tested offline."""

from __future__ import annotations

REPORT_SECTIONS = [
    "Overview",
    "Key players",
    "Injury impact",
    "Offensive tendencies",
    "Defensive notes",
    "Keys to the game",
]

# ---------------------------------------------------------------------------
# Part A: the fixed workflow (Messages API). Code decides every step.
# ---------------------------------------------------------------------------

FILM_SYSTEM = (
    "You are a football film analyst for a fictional league. You read play-by-play logs and write "
    "short, factual tendency notes. Only state what the plays show; say so when the sample is small."
)

REPORT_SYSTEM = (
    "You are the lead scout for a fictional football team. You write concise, practical scouting "
    "reports for coaches in Markdown. Use only the data you are given and never invent players or numbers."
)


def build_film_prompt(team: str, team_name: str, plays: str) -> str:
    return (
        f"<film>\n{plays}\n</film>\n\n"
        f"Write tendency notes on {team_name} ({team}) from this film: run/pass mix by down, "
        "big plays, red-zone and 4th-down behaviour, turnovers, and what their opponent did well against them. "
        "Return at most 12 bullet points."
    )


def build_report_prompt(team: str, team_name: str, stats: str, injuries: str, film_notes: str) -> str:
    headings = "\n".join(f"## {s}" for s in REPORT_SECTIONS)
    return (
        f"<stats>\n{stats}\n</stats>\n\n"
        f"<injuries>\n{injuries}\n</injuries>\n\n"
        f"<film_notes>\n{film_notes}\n</film_notes>\n\n"
        f"Write the scouting report on our next opponent, {team_name} ({team}). "
        f"Start with '# Scouting report: {team_name}' and use exactly these sections:\n{headings}\n"
        "Keep it under 600 words. Cite the numbers you rely on."
    )


# ---------------------------------------------------------------------------
# Part B: the agent (Agent SDK). The model decides the steps; these prompts set roles and rules.
# ---------------------------------------------------------------------------

FILM_AGENT_PROMPT = (
    "You are the film subagent of a scouting staff for a fictional football league. "
    "Use the get_plays tool to study the opponent's play-by-play. Filter by side and quarter instead of "
    "pulling everything at once. Report back at most 12 bullet points on tendencies (run/pass mix by down, "
    "big plays, red zone, 4th down, turnovers). Cite quarter and clock for each claim. "
    "If there is no film, say so in one line. Your final message is all the supervisor will see."
)

STATS_AGENT_PROMPT = (
    "You are the stats subagent of a scouting staff for a fictional football league. "
    "Use get_player_stats and get_injuries for the opponent. Report back: the 3-5 most important players "
    "with their key numbers and week-by-week trend, and every injury with its likely impact. "
    "At most 15 lines. Your final message is all the supervisor will see."
)


def build_supervisor_prompt(report_rel: str, notes_rel: str) -> str:
    """The supervisor's system prompt (a custom string, not the claude_code preset)."""
    headings = ", ".join(REPORT_SECTIONS)
    return (
        "You are the lead scout for a fictional football team. You plan the scouting report, delegate the "
        "research, and write the final report.\n"
        "- Delegate: send the 'film' subagent to study play-by-play and the 'stats' subagent to study stats and "
        "injuries. Each subagent sees only the task you give it, so name the team id in every delegation. "
        "Start both, then wait for both reports before writing.\n"
        "- Do not research the raw data yourself; work from the subagents' reports.\n"
        f"- Memory: if {notes_rel} exists, read it first; it holds notes from earlier sessions. At the end, "
        f"rewrite it with at most 10 bullets worth remembering next week (keep older bullets that still hold).\n"
        f"- Write the report to {report_rel} in Markdown with these sections: {headings}. Under 600 words.\n"
        "- Only write files under reports/."
    )


def build_agent_task(team: str, team_name: str, report_rel: str) -> str:
    return (
        f"Our next opponent is {team_name} ({team}). Produce the scouting report and save it to {report_rel}. "
        "Finish with a two-sentence summary of what you found."
    )
