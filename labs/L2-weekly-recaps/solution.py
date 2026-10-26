"""L2 reference solution: weekly recap batch job with a cached league context and a cost report.

Run from labs/ (each command is one step of the lab):
  uv run python L2-weekly-recaps/solution.py plan                      # token counts + projected cost per tier
  uv run python L2-weekly-recaps/solution.py compare                   # 3 realtime recaps per tier, measured
  uv run python L2-weekly-recaps/solution.py submit --tier haiku       # all 12 recaps as one batch
  uv run python L2-weekly-recaps/solution.py status                    # poll the batch
  uv run python L2-weekly-recaps/solution.py results                   # save recaps, report actual cost
  uv run python L2-weekly-recaps/solution.py submit --tier haiku --only por-w3,nsh-w3   # resubmit some
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

from gridiron.client import TIERS, client, log_usage
from l2_costs import Tokens, cost, project
from l2_recaps import LEAGUE_CONTEXT, all_jobs, build_params, build_requests, custom_id, foreign_players

LAB_DIR = Path(__file__).resolve().parent
OUT_DIR = LAB_DIR / "out"
BATCH_FILE = OUT_DIR / "batch.json"
SAMPLE = [("POR", 3), ("NSH", 3), ("BAL", 2)]  # the realtime comparison runs these on every tier
ASSUMED_OUTPUT = 800  # tokens per recap incl. thinking, for `plan`; replace with what `compare` measures


def text_of(message: Any) -> str:
    return "".join(b.text for b in message.content if b.type == "text")


def check_stop(message: Any) -> None:
    if message.stop_reason in ("max_tokens", "refusal"):
        raise RuntimeError(f"Unusable recap (stop_reason={message.stop_reason}).")


# --------------------------------------------------------------------------- #
# Step 2: plan. count_tokens is free, so measure before you spend.
# --------------------------------------------------------------------------- #


def plan() -> None:
    jobs = all_jobs()
    print(f"== {len(jobs)} recaps. Projected cost per tier (output assumed {ASSUMED_OUTPUT} tokens each)\n")
    print("| tier | shared | unique | realtime | realtime + 5m cache | batch | batch + 1h cache | same at 50% hits |")
    print("|---|---|---|---|---|---|---|---|")
    for tier, model in TIERS.items():
        team, week = jobs[0]
        shared = client.messages.count_tokens(model=model, system=LEAGUE_CONTEXT, messages=[{"role": "user", "content": "x"}])
        whole = client.messages.count_tokens(**_countable(build_params(team, week, model, cache="off")))
        shared_tokens = shared.input_tokens
        unique_tokens = whole.input_tokens - shared_tokens
        job = {"requests": len(jobs), "shared": shared_tokens, "unique": unique_tokens, "output": ASSUMED_OUTPUT}
        cols = [
            project(model, **job, batch=False, cache="off"),
            project(model, **job, batch=False, cache="5m"),
            project(model, **job, batch=True, cache="off"),
            project(model, **job, batch=True, cache="1h"),
            project(model, **job, batch=True, cache="1h", hit_rate=0.5),
        ]
        print(f"| {tier} | {shared_tokens} | {unique_tokens} | " + " | ".join(f"${c:.4f}" for c in cols) + " |")
    print("\nshared = the cached league context (must be over 512 tokens to cache at all).")


def _countable(params: dict[str, Any]) -> dict[str, Any]:
    """count_tokens takes the prompt, not generation settings."""
    return {k: v for k, v in params.items() if k in ("model", "system", "messages")}


# --------------------------------------------------------------------------- #
# Step 3: compare tiers on the same recaps, in realtime, with a 5-minute cache.
# --------------------------------------------------------------------------- #


def compare() -> None:
    rows = []
    for tier, model in TIERS.items():
        total, seconds, issues = Tokens(), 0.0, []
        print(f"\n== {tier} ({model})")
        for team, week in SAMPLE:
            started = time.perf_counter()
            message = client.messages.create(**build_params(team, week, model, cache="5m"))
            seconds += time.perf_counter() - started
            log_usage(f"{tier} {custom_id(team, week)}", message.usage)
            check_stop(message)
            recap = text_of(message)
            total += Tokens.from_usage(message.usage)
            if bad := foreign_players(recap, team):
                issues.append(f"{custom_id(team, week)} names {', '.join(bad)}")
            if (team, week) == SAMPLE[0]:
                print(recap)
        realtime = cost(model, total)
        rows.append((tier, seconds / len(SAMPLE), total, realtime, cost(model, total, batch=True), issues))

    report = ["| tier | s/recap | input | cache write | cache read | output | realtime $ | if batched $ | issues |", "|---|---|---|---|---|---|---|---|---|"]
    for tier, secs, t, rt, bt, issues in rows:
        writes = t.cache_write_5m + t.cache_write_1h
        report.append(
            f"| {tier} | {secs:.1f} | {t.input} | {writes} | {t.cache_read} | {t.output} | {rt:.5f} | {bt:.5f} | {'; '.join(issues) or 'none'} |"
        )
    OUT_DIR.mkdir(exist_ok=True)
    (OUT_DIR / "cost-report.md").write_text(f"# Recap cost report ({len(SAMPLE)} recaps per tier)\n\n" + "\n".join(report) + "\n")
    print("\n" + "\n".join(report))
    print(f"\nSaved to {OUT_DIR / 'cost-report.md'}. Pick the cheapest tier whose recaps pass your checks.")


# --------------------------------------------------------------------------- #
# Steps 4-5: the batch. Submit, poll, then collect results by custom_id.
# --------------------------------------------------------------------------- #


def submit(model: str, only: list[str] | None) -> None:
    jobs = all_jobs()
    if only:
        jobs = [j for j in jobs if custom_id(*j) in only]
        missing = set(only) - {custom_id(*j) for j in jobs}
        if missing:
            raise SystemExit(f"Unknown custom_id(s): {', '.join(sorted(missing))}")
    batch = client.messages.batches.create(requests=build_requests(model, jobs))
    OUT_DIR.mkdir(exist_ok=True)
    BATCH_FILE.write_text(json.dumps({"id": batch.id, "model": model}, indent=2) + "\n")
    print(f"Submitted {batch.id} with {len(jobs)} requests on {model}. Status: {batch.processing_status}")


def _saved_batch() -> dict[str, str]:
    if not BATCH_FILE.exists():
        raise SystemExit("No batch yet: run `submit` first.")
    return json.loads(BATCH_FILE.read_text())


def status() -> None:
    batch = client.messages.batches.retrieve(_saved_batch()["id"])
    c = batch.request_counts
    print(f"{batch.id}: {batch.processing_status} | processing {c.processing}, succeeded {c.succeeded}, "
          f"errored {c.errored}, canceled {c.canceled}, expired {c.expired}")


def collect(results: Any, model: str, out_dir: Path) -> dict[str, Any]:
    """Save each succeeded recap under its custom_id and sort out the rest.

    Results arrive in ANY order, so everything is keyed by custom_id, never by position.
    An invalid request fails the same way every time: fix it, don't resubmit it as is.
    Server-side errors and expired requests are safe to resubmit.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    total, usd, hits, saved = Tokens(), 0.0, 0, []
    fix, resubmit, issues = [], [], []
    for item in results:
        result = item.result
        if result.type == "succeeded":
            message = result.message
            if message.stop_reason in ("max_tokens", "refusal"):
                resubmit.append(item.custom_id)
                continue
            recap = text_of(message)
            (out_dir / f"{item.custom_id}.md").write_text(recap + "\n")
            saved.append(item.custom_id)
            tokens = Tokens.from_usage(message.usage)
            total += tokens
            usd += cost(model, tokens, batch=True)
            hits += tokens.cache_read > 0
            team = item.custom_id.split("-")[0].upper()
            if bad := foreign_players(recap, team):
                issues.append(f"{item.custom_id} names {', '.join(bad)}")
        elif result.type == "errored" and result.error.error.type == "invalid_request_error":
            fix.append(item.custom_id)
        else:  # other errors, canceled, expired: not billed, safe to try again
            resubmit.append(item.custom_id)
    return {
        "saved": sorted(saved),
        "fix": sorted(fix),
        "resubmit": sorted(resubmit),
        "issues": issues,
        "tokens": total,
        "usd": usd,
        "cache_hits": hits,
    }


def results() -> None:
    saved = _saved_batch()
    batch = client.messages.batches.retrieve(saved["id"])
    if batch.processing_status != "ended":
        raise SystemExit(f"{batch.id} is still {batch.processing_status}; try `status` again later.")
    r = collect(client.messages.batches.results(batch.id), saved["model"], OUT_DIR / "recaps")
    t = r["tokens"]
    print(f"Saved {len(r['saved'])} recaps to {OUT_DIR / 'recaps'}")
    print(f"Tokens: input {t.input}, cache write {t.cache_write_5m + t.cache_write_1h}, cache read {t.cache_read}, output {t.output}")
    if r["saved"]:
        print(f"Cache hits: {r['cache_hits']}/{len(r['saved'])} requests (best effort in batches)")
    print(f"Actual batch cost: ${r['usd']:.5f} (the same tokens in realtime: ${cost(saved['model'], t):.5f})")
    for label in ("fix", "resubmit", "issues"):
        if r[label]:
            print(f"{label}: {', '.join(r[label])}")
    if r["resubmit"]:
        print(f"Resubmit with: submit --model {saved['model']} --only {','.join(r['resubmit'])}")


def main() -> None:
    parser = argparse.ArgumentParser(description="L2 weekly recap batch job")
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


if __name__ == "__main__":
    main()
