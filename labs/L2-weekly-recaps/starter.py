"""L2 starter: weekly recap batch job with a cached league context and a cost report.

Run from labs/ (each command is one step of the lab; until its TODO is done it only explains itself):
  uv run python L2-weekly-recaps/starter.py plan
  uv run python L2-weekly-recaps/starter.py compare
  uv run python L2-weekly-recaps/starter.py submit --tier haiku
  uv run python L2-weekly-recaps/starter.py status
  uv run python L2-weekly-recaps/starter.py results

The requests, the cached prefix and the cost model are ready in l2_recaps.py and l2_costs.py.
Stuck? Compare with solution.py.
"""

from __future__ import annotations

import argparse
import json
import time  # noqa: F401
from pathlib import Path
from typing import Any

from gridiron.client import TIERS, client, log_usage  # noqa: F401
from l2_costs import Tokens, cost, project  # noqa: F401
from l2_recaps import LEAGUE_CONTEXT, all_jobs, build_params, build_requests, custom_id, foreign_players  # noqa: F401

LAB_DIR = Path(__file__).resolve().parent
OUT_DIR = LAB_DIR / "out"
BATCH_FILE = OUT_DIR / "batch.json"
SAMPLE = [("POR", 3), ("NSH", 3), ("BAL", 2)]
ASSUMED_OUTPUT = 800


def text_of(message: Any) -> str:
    return "".join(b.text for b in message.content if b.type == "text")


def plan() -> None:
    print(f"First request's user message:\n{build_params('POR', 3, TIERS['haiku'])['messages'][0]['content']}\n")
    # TODO 1: measure before you spend. For each tier in TIERS:
    #   shared = client.messages.count_tokens(model=..., system=LEAGUE_CONTEXT,
    #                                         messages=[{"role": "user", "content": "x"}]).input_tokens
    #   whole  = count_tokens on build_params(team, week, model, cache="off"), passing only
    #            model, system and messages. unique = whole - shared.
    #   Then print project(model, requests=12, shared=..., unique=..., output=ASSUMED_OUTPUT,
    #   batch=..., cache=...) for: realtime without cache, realtime + "5m", batch without cache,
    #   batch + "1h", and batch + "1h" with hit_rate=0.5.
    #   Is `shared` above 512 tokens on every tier? Below that, caching silently does nothing.
    raise NotImplementedError("TODO 1: plan")


def compare() -> None:
    # TODO 2: for each tier, create the SAMPLE recaps in realtime, one after another:
    #   message = client.messages.create(**build_params(team, week, model, cache="5m"))
    #   time each call, log_usage(...), check message.stop_reason is not "max_tokens"/"refusal",
    #   add Tokens.from_usage(message.usage) to a running total, and run foreign_players(text, team).
    #   Report per tier: seconds per recap, the token split, cost(model, total) and
    #   cost(model, total, batch=True). The first call should WRITE the cache, later ones READ it.
    raise NotImplementedError("TODO 2: compare")


def submit(model: str, only: list[str] | None) -> None:
    jobs = [j for j in all_jobs() if not only or custom_id(*j) in only]
    # TODO 3: batch = client.messages.batches.create(requests=build_requests(model, jobs))
    #   Save {"id": batch.id, "model": model} to BATCH_FILE: you need both to collect the results.
    _ = jobs
    raise NotImplementedError("TODO 3: submit")


def status() -> None:
    # TODO 4: client.messages.batches.retrieve(id) and print processing_status and request_counts.
    raise NotImplementedError("TODO 4: status")


def collect(results: Any, model: str, out_dir: Path) -> dict[str, Any]:
    """Save each succeeded recap under its custom_id and sort out the rest."""
    # TODO 5: for each item in results (they arrive in ANY order, so key on item.custom_id):
    #   item.result.type == "succeeded": skip if message.stop_reason is max_tokens/refusal
    #       (resubmit those), else write out_dir/<custom_id>.md, add Tokens.from_usage(usage),
    #       add cost(model, tokens, batch=True), count a cache hit when tokens.cache_read > 0.
    #   "errored" with item.result.error.error.type == "invalid_request_error": a "fix" list.
    #       Resubmitting an invalid request fails the same way.
    #   anything else (other errors, "canceled", "expired"): a "resubmit" list.
    #   Return {"saved", "fix", "resubmit", "issues", "tokens", "usd", "cache_hits"}.
    raise NotImplementedError("TODO 5: collect")


def results() -> None:
    saved = json.loads(BATCH_FILE.read_text()) if BATCH_FILE.exists() else None
    if saved is None:
        raise SystemExit("No batch yet: run `submit` first.")
    batch = client.messages.batches.retrieve(saved["id"])
    if batch.processing_status != "ended":
        raise SystemExit(f"{batch.id} is still {batch.processing_status}; try `status` again later.")
    r = collect(client.messages.batches.results(batch.id), saved["model"], OUT_DIR / "recaps")
    print(f"Saved {len(r['saved'])} recaps, cache hits {r['cache_hits']}, batch cost ${r['usd']:.5f}")
    for label in ("fix", "resubmit", "issues"):
        if r[label]:
            print(f"{label}: {', '.join(r[label])}")


def main() -> None:
    parser = argparse.ArgumentParser(description="L2 weekly recap batch job (starter)")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("plan")
    sub.add_parser("compare")
    s = sub.add_parser("submit")
    s.add_argument("--tier", choices=TIERS, default="haiku")
    s.add_argument("--model", help="exact model id (overrides --tier)")
    s.add_argument("--only", help="comma-separated custom_ids to (re)submit")
    sub.add_parser("status")
    sub.add_parser("results")
    args = parser.parse_args()

    try:
        if args.command == "plan":
            plan()
        elif args.command == "compare":
            compare()
        elif args.command == "submit":
            submit(args.model or TIERS[args.tier], args.only.split(",") if args.only else None)
        elif args.command == "status":
            status()
        else:
            results()
    except NotImplementedError as todo:
        print(f"Not built yet: {todo}. No API calls were made.")


if __name__ == "__main__":
    main()
