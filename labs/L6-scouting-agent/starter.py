"""L6 Scouting report agent: starter.

Build the same scouting report twice and compare:
  Part A: a fixed workflow on the Messages API (TODO 1-2)
  Part B: an Agent SDK supervisor with "film" and "stats" subagents, custom tools,
          least-privilege permissions and a PreToolUse hook (TODO 3-7)
  Stretch: memory across sessions (TODO 8)

Provided for you:
  l6_data.py    compact text views of a team's stats, injuries and film, plus report_path()
  l6_tools.py   an in-process SDK MCP server "gridiron" with three read-only tools
  l6_prompts.py system prompts and prompt builders for both parts
solution.py, l6_hooks.py and the test_l6_*.py files show one finished version. Try first.

Run from labs/:
  uv run python L6-scouting-agent/starter.py            # offline: shows which TODOs are done
  uv run --env-file .env python L6-scouting-agent/starter.py workflow NSH
  uv run --env-file .env python L6-scouting-agent/starter.py agent NSH
Without ANTHROPIC_API_KEY (or --live) it makes no API calls and exits cleanly.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import time
from pathlib import Path
from typing import Any

from claude_agent_sdk import AgentDefinition, ClaudeAgentOptions, HookMatcher, ResultMessage, query  # noqa: F401

from gridiron.client import MODEL, TIERS, client, log_usage  # noqa: F401
from l6_data import LAB_DIR, REPORTS_DIR, format_injuries, format_plays, format_stats, report_path, team_name  # noqa: F401
from l6_prompts import (  # noqa: F401
    FILM_AGENT_PROMPT,
    FILM_SYSTEM,
    REPORT_SYSTEM,
    STATS_AGENT_PROMPT,
    build_agent_task,
    build_film_prompt,
    build_report_prompt,
    build_supervisor_prompt,
)
from l6_tools import SERVER_NAME, build_server, tool_name  # noqa: F401

# ---------------------------------------------------------------------------
# Part A: the fixed workflow. Your code decides every step.
# ---------------------------------------------------------------------------


def gather(team: str) -> dict[str, str]:
    """TODO 1: collect the inputs in a fixed order, with no model involved.

    Return {"team", "name", "stats", "injuries", "plays"}.
    Hint: team_name(), format_stats(), format_injuries() and format_plays() from l6_data.
    """
    raise NotImplementedError("TODO 1")


def run_workflow(team: str) -> None:
    """TODO 2: two Claude calls, then save the report.

    a) film_notes = one call with system=FILM_SYSTEM and build_film_prompt(...)
    b) report = one call with system=REPORT_SYSTEM and build_report_prompt(..., film_notes)
    c) write it to report_path(team) (mkdir the parent first)
    Hints:
    - client.messages.create(model=MODEL, max_tokens=16000, system=..., messages=[{"role": "user", "content": ...}])
    - check response.stop_reason == "end_turn"; join the text blocks (block.type == "text")
    - log_usage(label, response.usage), and add up input/output tokens and time.perf_counter() for the comparison
    """
    raise NotImplementedError("TODO 2")


# ---------------------------------------------------------------------------
# Part B: the agent. The model decides the steps; your code sets the boundaries.
# ---------------------------------------------------------------------------


def write_denial_reason(tool_name: str, tool_input: dict[str, Any], cwd: Path, reports_dir: Path) -> str | None:
    """TODO 3: the pure path check behind the hook. Return a reason to deny, or None to allow.

    - Only Write and Edit (key "file_path") and NotebookEdit (key "notebook_path") are write tools;
      return None for any other tool.
    - Resolve a relative path against cwd, then .resolve() so ".." and symlinks can't escape.
    - Allow only paths strictly inside reports_dir (Path.is_relative_to); deny a missing path.
    """
    raise NotImplementedError("TODO 3")


async def guard_reports(input_data: dict[str, Any], tool_use_id: str | None, context: Any) -> dict[str, Any]:
    """TODO 4: the PreToolUse hook callback.

    Call write_denial_reason(input_data["tool_name"], input_data["tool_input"], Path(input_data["cwd"]), REPORTS_DIR).
    Allow: return {}. Deny: return the documented shape
      {"hookSpecificOutput": {"hookEventName": "PreToolUse",
                              "permissionDecision": "deny",
                              "permissionDecisionReason": reason}}
    """
    raise NotImplementedError("TODO 4")


def subagents() -> dict[str, AgentDefinition]:
    """TODO 5: define the "film" and "stats" subagents.

    Each needs a description (when to use it), a prompt (FILM_AGENT_PROMPT / STATS_AGENT_PROMPT)
    and a narrow tools list built with tool_name(...):
      film:  get_plays only
      stats: get_player_stats and get_injuries
    Optional: model=TIERS["haiku"] for the stats reader.
    """
    raise NotImplementedError("TODO 5")


def build_options(team: str, resume: str | None = None) -> ClaudeAgentOptions:
    """TODO 6: ClaudeAgentOptions with a deliberate choice for each line.

    - model=MODEL
    - system_prompt: build_supervisor_prompt(report_rel, notes_rel) as a custom string
      (or the {"type": "preset", "preset": "claude_code"} preset; say why you chose one)
    - setting_sources=[]  (don't load CLAUDE.md or settings from disk)
    - cwd=str(LAB_DIR)
    - tools=["Agent", "Read", "Write"]        (availability: no Bash)
    - allowed_tools=[...] (permission: Agent, Write and the three mcp__gridiron__ tools)
    - permission_mode="dontAsk"               (anything else is denied, not prompted)
    - mcp_servers={SERVER_NAME: build_server()}, agents=subagents()
    - hooks={"PreToolUse": [HookMatcher(matcher="Write|Edit|NotebookEdit", hooks=[guard_reports])]}
    - max_turns and max_budget_usd as a spend cap; resume=resume
    """
    raise NotImplementedError("TODO 6")


async def run_agent(team: str, resume: str | None = None) -> None:
    """TODO 7: run the supervisor and print the numbers you need for the comparison.

    async for message in query(prompt=build_agent_task(...), options=build_options(team, resume)):
      - AssistantMessage: print ToolUseBlock names; parent_tool_use_id is set inside a subagent
      - ResultMessage: print subtype, num_turns, duration_ms, usage, total_cost_usd, session_id
    """
    raise NotImplementedError("TODO 7")


# TODO 8 (stretch): memory across sessions.
#   a) Save ResultMessage.session_id to reports/.last-session and pass it as resume= next run.
#   b) Or let the supervisor keep reports/notes/<team>-notes.md (already in its prompt).
#   Then ask a follow-up ("what changed since last week?") and see what it remembers.


# ---------------------------------------------------------------------------
# Offline progress check and CLI. No API calls happen here.
# ---------------------------------------------------------------------------


def _done(fn, *args) -> str:
    try:
        result = fn(*args)
        if asyncio.iscoroutine(result):
            result = asyncio.run(result)
        return "done"
    except NotImplementedError:
        return "todo"
    except Exception as e:  # a half-finished TODO shouldn't crash the check
        return f"error: {type(e).__name__}: {e}"


def progress(team: str) -> None:
    hook_input = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Write",
        "tool_input": {"file_path": "../gridiron/data.py"},
        "cwd": str(LAB_DIR),
    }
    print(f"L6 starter, team {team}. Offline progress (no API calls):")
    print(f"  TODO 1 gather ... {_done(gather, team)}")
    print("  TODO 2 run_workflow ... needs a key; run `starter.py workflow` when TODO 1 is done")
    print(f"  TODO 3 path check ... {_done(write_denial_reason, 'Write', {'file_path': 'x.md'}, LAB_DIR, REPORTS_DIR)}")
    print(f"  TODO 4 hook callback ... {_done(guard_reports, hook_input, None, None)}")
    print(f"  TODO 5 subagents ... {_done(subagents)}")
    print(f"  TODO 6 options ... {_done(build_options, team)}")
    print("  TODO 7 run_agent ... needs a key; run `starter.py agent` when TODO 3-6 are done")


def main() -> None:
    parser = argparse.ArgumentParser(description="L6 starter")
    parser.add_argument("mode", nargs="?", choices=["check", "workflow", "agent"], default="check")
    parser.add_argument("team", nargs="?", default="NSH")
    parser.add_argument("--live", action="store_true", help="call Claude even without ANTHROPIC_API_KEY (ant auth login)")
    args = parser.parse_args()
    team = args.team.upper()
    team_name(team)

    has_key = bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")) or args.live
    if args.mode == "check" or not has_key:
        if args.mode != "check":
            print("No ANTHROPIC_API_KEY in the environment, so no API calls were made.\n")
        progress(team)
        return
    start = time.perf_counter()
    if args.mode == "workflow":
        run_workflow(team)
    else:
        asyncio.run(run_agent(team))
    print(f"wall time {time.perf_counter() - start:.1f}s")


if __name__ == "__main__":
    main()
