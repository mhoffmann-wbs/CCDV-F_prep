"""L4 starter: fantasy lineup assistant with a manual tool-use loop.

Run from labs/:  uv run python L4-lineup-assistant/starter.py
Fill in the numbered TODOs in order. Until TODO 2 is done, the script makes no API calls:
it prints what Claude would see (the tool names and the roster tool's output).
The tools, schemas and rules are ready in l4_tools.py and l4_league.py.
Stuck? Compare with solution.py.
"""

from __future__ import annotations

import argparse
import functools
from collections.abc import Callable
from typing import Any

from gridiron.client import MODEL, client, log_usage
from l4_league import LineupStore
from l4_tools import READ_ONLY, SYSTEM_PROMPT, TOOL_NAMES, TOOLS, Approver, run_tool, tool_result  # noqa: F401

DEFAULT_REQUEST = "Set my week 4 lineup. Start the best healthy players and tell me about any close calls."
MAX_TURNS = 10

# TODO 3 (step 5): server-side context editing. Fill in one clear_tool_uses_20250919 edit:
#   trigger after 6 tool uses, keep the 2 most recent, never clear set_lineup.
CLEAR_OLD_RESULTS: dict[str, Any] = {"edits": []}


def check_stop(message: Any) -> None:
    """Raise before any content is used, and before any tool runs, if the turn can't be trusted."""
    # TODO 0: raise RuntimeError when message.stop_reason is "refusal" or "max_tokens".
    #   Why before the tools: a tool_use block cut off at max_tokens may carry a truncated input.
    pass


def run_tool_calls(calls: list[Any], *, approve: Approver, store: LineupStore) -> list[dict[str, Any]]:
    """Run every tool_use block from ONE assistant turn and return their tool_result blocks."""
    # TODO 1: for each call, run_tool(call.name, call.input, approve=approve, store=store)
    #   and wrap the outcome with tool_result(call.id, outcome). Keep the calls' order.
    #   Stretch: run the READ_ONLY calls concurrently (ThreadPoolExecutor), side effects serially.
    raise NotImplementedError("TODO 1")


def run_assistant(
    request: str,
    *,
    create: Callable[..., Any],
    approve: Approver,
    store: LineupStore,
    max_turns: int = MAX_TURNS,
    on_turn: Callable[[int, Any], None] | None = None,
) -> tuple[str, list[dict[str, Any]]]:
    """The manual agentic loop. Returns the final text and the full transcript."""
    messages: list[dict[str, Any]] = [{"role": "user", "content": request}]
    # TODO 2: the loop, at most max_turns times:
    #   response = create(system=SYSTEM_PROMPT, tools=TOOLS, messages=messages)
    #   call on_turn(turn, response) if given, then check_stop(response)
    #   append {"role": "assistant", "content": response.content}  <- the WHOLE content, unchanged
    #   if response.stop_reason != "tool_use": return the joined text blocks and messages
    #   otherwise collect the tool_use blocks, run them with run_tool_calls, and append
    #   ALL their results as ONE {"role": "user", "content": [...]} message.
    #   After max_turns, raise RuntimeError instead of looping forever.
    _ = messages
    raise NotImplementedError("TODO 2")


def ask_user(preview: str) -> bool:
    print(f"\n{preview}")
    return input("Save this lineup? [y/N] ").strip().lower() in ("y", "yes")


def main() -> None:
    parser = argparse.ArgumentParser(description="L4 fantasy lineup assistant (starter)")
    parser.add_argument("request", nargs="?", default=DEFAULT_REQUEST)
    parser.add_argument("--serial", action="store_true", help="disable parallel tool use (one call per turn)")
    parser.add_argument("--clear-old", action="store_true", help="clear old tool results server-side")
    parser.add_argument("--yes", action="store_true", help="approve set_lineup without asking")
    args = parser.parse_args()

    params: dict[str, Any] = {"model": MODEL, "max_tokens": 16000, "output_config": {"effort": "medium"}}
    # TODO 4 (step 4): if args.serial, set params["tool_choice"] to auto with parallel tool use disabled.
    #   Don't reach for {"type": "any"} or {"type": "tool"}: forced tool use is a 400 on current models.
    create = functools.partial(client.messages.create, **params)
    # TODO 3 (step 5): if args.clear_old, use client.beta.messages.create instead, with
    #   betas=["context-management-2025-06-27"] and context_management=CLEAR_OLD_RESULTS.

    def on_turn(turn: int, response: Any) -> None:
        log_usage(f"turn {turn}", response.usage)
        for c in (b for b in response.content if b.type == "tool_use"):
            print(f"  -> {c.name}({c.input})")

    print(f"== {args.request} ({MODEL})")
    try:
        text, messages = run_assistant(
            args.request,
            create=create,
            approve=(lambda _: True) if args.yes else ask_user,
            store=LineupStore(),
            on_turn=on_turn,
        )
    except NotImplementedError as todo:
        print(f"\nNothing called yet ({todo} is next). Claude will see these tools: {', '.join(TOOL_NAMES)}")
        print("get_roster would return:\n")
        print(run_tool("get_roster", {}, approve=lambda _: False, store=LineupStore()).content)
        return

    print(f"\n{text}\n")
    print(f"== {sum(1 for m in messages if m['role'] == 'assistant')} turns")


if __name__ == "__main__":
    main()
