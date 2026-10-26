"""L4 reference solution: fantasy lineup assistant with a manual tool-use loop.

Run from labs/:
  uv run python L4-lineup-assistant/solution.py
  uv run python L4-lineup-assistant/solution.py "Who should be my FLEX this week?"
  uv run python L4-lineup-assistant/solution.py --serial      # one tool call per turn
  uv run python L4-lineup-assistant/solution.py --clear-old   # server-side context editing
  uv run python L4-lineup-assistant/solution.py --yes         # approve set_lineup without asking
"""

from __future__ import annotations

import argparse
import functools
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import anthropic

from gridiron.client import MODEL, client, log_usage
from l4_league import LineupStore
from l4_tools import READ_ONLY, SYSTEM_PROMPT, TOOLS, Approver, run_tool, tool_result

DEFAULT_REQUEST = "Set my week 4 lineup. Start the best healthy players and tell me about any close calls."
MAX_TURNS = 10

# Server-side context editing: once 6 tool uses have piled up, the API replaces
# the oldest tool results with a placeholder, keeping the 2 most recent. It edits
# the server's copy only; your `messages` list stays append-only, so the prompt
# prefix (and the thinking blocks tied to it) stays valid.
CLEAR_OLD_RESULTS = {
    "edits": [
        {
            "type": "clear_tool_uses_20250919",
            "trigger": {"type": "tool_uses", "value": 6},
            "keep": {"type": "tool_uses", "value": 2},
            "exclude_tools": ["set_lineup"],
        }
    ]
}


def check_stop(message: Any) -> None:
    """Raise before any content is used, and before any tool runs, if the turn can't be trusted."""
    if message.stop_reason == "refusal":
        details = message.stop_details
        raise RuntimeError(f"Claude declined (refusal, category={details.category if details else None}).")
    if message.stop_reason == "max_tokens":
        # A tool_use block cut off here may hold a truncated input. Never run it.
        raise RuntimeError("Output was cut off at max_tokens; raise max_tokens and retry the turn.")


def run_tool_calls(calls: list[Any], *, approve: Approver, store: LineupStore) -> list[dict[str, Any]]:
    """Run every tool_use block from ONE assistant turn and return their tool_result blocks.

    Read-only calls run concurrently; calls with side effects run one at a time.
    The results keep the order of the calls, and all of them go back to Claude in
    a single user message (splitting them teaches Claude to stop calling in parallel).
    """

    def run(call: Any) -> dict[str, Any]:
        return tool_result(call.id, run_tool(call.name, call.input, approve=approve, store=store))

    read_only = [c for c in calls if c.name in READ_ONLY]
    with ThreadPoolExecutor() as pool:
        done = dict(zip((c.id for c in read_only), pool.map(run, read_only)))
    for call in calls:
        if call.id not in done:
            done[call.id] = run(call)
    return [done[c.id] for c in calls]


def run_assistant(
    request: str,
    *,
    create: Callable[..., Any],
    approve: Approver,
    store: LineupStore,
    max_turns: int = MAX_TURNS,
    on_turn: Callable[[int, Any], None] | None = None,
) -> tuple[str, list[dict[str, Any]]]:
    """The manual agentic loop. Returns the final text and the full transcript.

    `create` is client.messages.create (or a stand-in in tests), so the loop
    itself has no hidden dependencies.
    """
    messages: list[dict[str, Any]] = [{"role": "user", "content": request}]
    for turn in range(1, max_turns + 1):
        response = create(system=SYSTEM_PROMPT, tools=TOOLS, messages=messages)
        if on_turn:
            on_turn(turn, response)
        check_stop(response)

        # Append the WHOLE content (thinking, text and tool_use blocks), unchanged.
        # The next request must show Claude its own calls, and editing earlier
        # turns would invalidate the cache and the thinking blocks after the edit.
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason != "tool_use":
            text = "".join(b.text for b in response.content if b.type == "text")
            return text, messages

        calls = [b for b in response.content if b.type == "tool_use"]
        messages.append({"role": "user", "content": run_tool_calls(calls, approve=approve, store=store)})

    raise RuntimeError(f"Stopped after {max_turns} turns without a final answer.")


def ask_user(preview: str) -> bool:
    print(f"\n{preview}")
    return input("Save this lineup? [y/N] ").strip().lower() in ("y", "yes")


def main() -> None:
    parser = argparse.ArgumentParser(description="L4 fantasy lineup assistant")
    parser.add_argument("request", nargs="?", default=DEFAULT_REQUEST)
    parser.add_argument("--serial", action="store_true", help="disable parallel tool use (one call per turn)")
    parser.add_argument("--clear-old", action="store_true", help="clear old tool results server-side")
    parser.add_argument("--yes", action="store_true", help="approve set_lineup without asking")
    args = parser.parse_args()

    params: dict[str, Any] = {"model": MODEL, "max_tokens": 16000, "output_config": {"effort": "medium"}}
    if args.serial:
        # tool_choice "auto" is the default; "any"/"tool" (forced use) are a 400 on current models.
        params["tool_choice"] = {"type": "auto", "disable_parallel_tool_use": True}
    if args.clear_old:
        create = functools.partial(
            client.beta.messages.create,
            betas=["context-management-2025-06-27"],
            context_management=CLEAR_OLD_RESULTS,
            **params,
        )
    else:
        create = functools.partial(client.messages.create, **params)

    totals = {"input": 0, "output": 0, "calls": 0}

    def on_turn(turn: int, response: Any) -> None:
        calls = [b for b in response.content if b.type == "tool_use"]
        totals["input"] += response.usage.input_tokens
        totals["output"] += response.usage.output_tokens
        totals["calls"] += len(calls)
        log_usage(f"turn {turn}", response.usage)
        for c in calls:
            print(f"  -> {c.name}({c.input})")
        edits = getattr(response, "context_management", None)
        if edits and edits.applied_edits:
            for e in edits.applied_edits:
                print(f"  [context editing] cleared {e.cleared_tool_uses} tool uses, {e.cleared_input_tokens} tokens")

    print(f"== {args.request} ({MODEL})")
    try:
        text, messages = run_assistant(
            args.request,
            create=create,
            approve=(lambda _: True) if args.yes else ask_user,
            store=LineupStore(),
            on_turn=on_turn,
        )
    except anthropic.APIStatusError as e:
        raise SystemExit(f"API error {e.status_code}: {e.message}") from e

    print(f"\n{text}\n")
    turns = sum(1 for m in messages if m["role"] == "assistant")
    print(f"== {turns} turns, {totals['calls']} tool calls, {totals['input']} input + {totals['output']} output tokens")


if __name__ == "__main__":
    main()
