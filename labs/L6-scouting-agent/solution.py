"""L6 Scouting report agent: reference solution.

Two ways to build the same scouting report on an upcoming opponent:

  Part A, the fixed workflow (Messages API): code gathers stats, injuries and film in a
  fixed order, then makes two Claude calls (film notes, then the report).

  Part B, the agent (Claude Agent SDK): a supervisor delegates to a "film" and a "stats"
  subagent, which reach the data through custom read-only tools. A PreToolUse hook
  denies any write outside reports/. Notes in reports/notes/ and an optional session
  resume give it memory across sessions.

Run from labs/:
  uv run python L6-scouting-agent/solution.py workflow NSH
  uv run python L6-scouting-agent/solution.py agent NSH
  uv run python L6-scouting-agent/solution.py agent NSH --resume
  uv run python L6-scouting-agent/solution.py check      # offline self-check, no API calls
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
import time
from pathlib import Path

from claude_agent_sdk import (
    AgentDefinition,
    AssistantMessage,
    ClaudeAgentOptions,
    HookMatcher,
    ResultMessage,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
    query,
)

from gridiron.client import MODEL, TIERS, client, log_usage
from l6_data import LAB_DIR, REPORTS_DIR, format_injuries, format_plays, format_stats, report_path, team_name
from l6_hooks import WRITE_MATCHER, make_reports_guard, write_denial_reason
from l6_prompts import (
    FILM_AGENT_PROMPT,
    FILM_SYSTEM,
    REPORT_SYSTEM,
    STATS_AGENT_PROMPT,
    build_agent_task,
    build_film_prompt,
    build_report_prompt,
    build_supervisor_prompt,
)
from l6_tools import SERVER_NAME, build_server, tool_name

# USD per million tokens (input, output), for the workflow's cost estimate.
# Check current prices at https://platform.claude.com/docs/en/about-claude/pricing
PRICES = {TIERS["opus"]: (4.00, 20.00), TIERS["sonnet"]: (2.00, 10.00), TIERS["haiku"]: (0.10, 0.50)}

SESSION_FILE = REPORTS_DIR / ".last-session"


def notes_path(team: str) -> Path:
    return REPORTS_DIR / "notes" / f"{team.lower()}-notes.md"


def has_credentials() -> bool:
    """True when a key or token is in the environment. `ant auth login` users pass --live instead."""
    return bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"))


# ---------------------------------------------------------------------------
# Part A: the fixed workflow
# ---------------------------------------------------------------------------


def gather(team: str) -> dict[str, str]:
    """Step 1 (code, no model): collect everything the report needs, in a fixed order."""
    return {
        "team": team,
        "name": team_name(team),
        "stats": format_stats(team),
        "injuries": format_injuries(team),
        "plays": format_plays(team),
    }


def build_workflow_prompts(data: dict[str, str]) -> tuple[str, str]:
    """The film prompt, and a report prompt with a placeholder for the film notes (filled after call 1)."""
    film = build_film_prompt(data["team"], data["name"], data["plays"])
    report = build_report_prompt(data["team"], data["name"], data["stats"], data["injuries"], "{film_notes}")
    return film, report


def ask(system: str, prompt: str, label: str, totals: dict[str, int]) -> str:
    response = client.messages.create(
        model=MODEL,
        max_tokens=16000,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    log_usage(label, response.usage)
    totals["input"] += response.usage.input_tokens
    totals["output"] += response.usage.output_tokens
    if response.stop_reason != "end_turn":
        raise RuntimeError(f"{label}: stopped with {response.stop_reason!r}, not end_turn")
    return "".join(b.text for b in response.content if b.type == "text")


def run_workflow(team: str) -> None:
    start = time.perf_counter()
    totals = {"input": 0, "output": 0}
    data = gather(team)
    film_prompt, report_prompt = build_workflow_prompts(data)

    # Step 2: film notes (skip the call when there is no film, a decision code can make).
    if data["plays"].startswith("No play-by-play"):
        film_notes = data["plays"]
    else:
        film_notes = ask(FILM_SYSTEM, film_prompt, "film", totals)

    # Step 3: the report. Step 4 (code): save it.
    report = ask(REPORT_SYSTEM, report_prompt.replace("{film_notes}", film_notes), "report", totals)
    out = report_path(team)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(report + "\n")

    seconds = time.perf_counter() - start
    price_in, price_out = PRICES.get(MODEL, (0.0, 0.0))
    cost = totals["input"] / 1e6 * price_in + totals["output"] / 1e6 * price_out
    print(f"\nWorkflow wrote {out.relative_to(LAB_DIR)}")
    print(f"latency={seconds:.1f}s calls=2 input={totals['input']} output={totals['output']} est_cost=${cost:.4f}")


# ---------------------------------------------------------------------------
# Part B: the agent
# ---------------------------------------------------------------------------


def build_options(team: str, resume: str | None = None, lab_dir: Path = LAB_DIR) -> ClaudeAgentOptions:
    reports_dir = lab_dir / "reports"
    film = AgentDefinition(
        description="Film analyst. Use to study an opponent's play-by-play for tendencies.",
        prompt=FILM_AGENT_PROMPT,
        tools=[tool_name("get_plays")],  # least privilege: film only
        model=TIERS["sonnet"],
    )
    stats = AgentDefinition(
        description="Stats analyst. Use for an opponent's player stats, trends and injury report.",
        prompt=STATS_AGENT_PROMPT,
        tools=[tool_name("get_player_stats"), tool_name("get_injuries")],  # stats and injuries only
        model=TIERS["haiku"],  # reading-heavy, simple work goes to a cheaper model
    )
    report_rel = str(report_path(team).relative_to(LAB_DIR))
    notes_rel = str(notes_path(team).relative_to(LAB_DIR))
    return ClaudeAgentOptions(
        model=MODEL,
        # A custom string, not the claude_code preset: this is a scouting agent, not a coding agent,
        # and we want its role and rules on every turn. (No system_prompt = the minimal default.)
        system_prompt=build_supervisor_prompt(report_rel, notes_rel),
        # Isolation: don't load ~/.claude or project settings, CLAUDE.md, skills or hooks from disk.
        setting_sources=[],
        cwd=str(lab_dir),
        # Availability: the only built-ins in context. No Bash, so no shell writes around the hook.
        tools=["Agent", "Read", "Write"],
        # Permission: these run without a prompt. Reads inside cwd need no rule.
        allowed_tools=["Agent", "Write", tool_name("get_player_stats"), tool_name("get_injuries"), tool_name("get_plays")],
        # Anything that would prompt is denied instead (subagents inherit this mode).
        permission_mode="dontAsk",
        mcp_servers={SERVER_NAME: build_server()},
        agents={"film": film, "stats": stats},
        # The guarantee: deny writes outside reports/, in every permission mode, for every agent.
        hooks={"PreToolUse": [HookMatcher(matcher=WRITE_MATCHER, hooks=[make_reports_guard(reports_dir)])]},
        max_turns=30,
        max_budget_usd=1.00,
        resume=resume,
    )


async def run_agent(team: str, resume: bool = False) -> None:
    session = SESSION_FILE.read_text().strip() if resume and SESSION_FILE.exists() else None
    if resume and not session:
        print("No earlier session found; starting a new one.")
    notes_path(team).parent.mkdir(parents=True, exist_ok=True)
    options = build_options(team, resume=session)
    report_rel = str(report_path(team).relative_to(LAB_DIR))
    prompt = build_agent_task(team, team_name(team), report_rel)

    start = time.perf_counter()
    async for message in query(prompt=prompt, options=options):
        if isinstance(message, AssistantMessage):
            who = "  [subagent]" if message.parent_tool_use_id else "[supervisor]"
            for block in message.content:
                if isinstance(block, ToolUseBlock):
                    target = block.input.get("subagent_type") or block.input.get("file_path") or block.input.get("team") or ""
                    print(f"{who} {block.name} {target}")
                elif isinstance(block, TextBlock) and not message.parent_tool_use_id:
                    print(f"{who} {block.text.strip()[:200]}")
        elif isinstance(message, UserMessage) and isinstance(message.content, list):
            # Tool results come back as user messages. Show failures, including hook denials.
            for block in message.content:
                if isinstance(block, ToolResultBlock) and block.is_error:
                    print(f"  [tool error] {str(block.content)[:200]}")
        elif isinstance(message, ResultMessage):
            seconds = time.perf_counter() - start
            SESSION_FILE.write_text(message.session_id)  # memory: resume this session next time
            usage = message.usage or {}
            print(f"\nAgent finished: {message.subtype} (is_error={message.is_error}), turns={message.num_turns}")
            print(
                f"latency={seconds:.1f}s api_time={message.duration_api_ms / 1000:.1f}s "
                f"input={usage.get('input_tokens')} cache_read={usage.get('cache_read_input_tokens')} "
                f"output={usage.get('output_tokens')} cost=${message.total_cost_usd or 0:.4f}"
            )
            # Per model, so the subagents' cheaper models show up separately. Costs are client-side estimates.
            for model, mu in (message.model_usage or {}).items():
                print(f"  {model}: input={mu.get('inputTokens')} output={mu.get('outputTokens')} cost=${mu.get('costUSD', 0):.4f}")
            if message.permission_denials:
                print(f"permission denials: {message.permission_denials}")
            if message.result:
                print(message.result)


# ---------------------------------------------------------------------------
# Offline self-check and CLI
# ---------------------------------------------------------------------------


def self_check(team: str) -> None:
    data = gather(team)
    film_prompt, report_prompt = build_workflow_prompts(data)
    print(f"Workflow data for {data['name']}: film prompt {len(film_prompt)} chars, report prompt {len(report_prompt)} chars")
    report_rel = str(report_path(team).relative_to(LAB_DIR))
    for path in (report_rel, "solution.py", "reports/../solution.py"):
        reason = write_denial_reason("Write", {"file_path": path}, LAB_DIR, REPORTS_DIR)
        print(f"hook: Write {path} -> {'deny' if reason else 'allow'}")
    options = build_options(team)
    print(f"agent: tools={options.tools} subagents={list(options.agents or {})} mode={options.permission_mode}")
    print(f"report target: {report_rel}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("mode", choices=["workflow", "agent", "check"])
    parser.add_argument("team", nargs="?", default="NSH")
    parser.add_argument("--resume", action="store_true", help="agent: resume the last saved session")
    parser.add_argument("--live", action="store_true", help="call Claude even without a key in the environment")
    args = parser.parse_args()
    team = args.team.upper()
    team_name(team)  # fail fast on an unknown team

    if args.mode == "check":
        self_check(team)
        return
    if not (has_credentials() or args.live):
        print("No ANTHROPIC_API_KEY in the environment, so no API calls were made. Offline check instead:\n")
        self_check(team)
        return
    if args.mode == "workflow":
        run_workflow(team)
    else:
        asyncio.run(run_agent(team, resume=args.resume))


if __name__ == "__main__":
    sys.exit(main())
