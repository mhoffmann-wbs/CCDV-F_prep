"""L10 starter: ship the weekly recap job.

Run from labs/:
  uv run python L10-ship-it/starter.py gate                      # gate release.json (today's prod)
  uv run python L10-ship-it/starter.py adr                       # write the platform decision record
  uv run python L10-ship-it/starter.py lock recap@v2             # record a prompt version as released
  uv run python L10-ship-it/starter.py smoke                     # live: Models API + one recap in dev

Fill in the numbered TODOs. A check that isn't written yet reports "todo" and blocks the release.
Stuck? Compare with solution.py.
  uv run python L10-ship-it/starter.py smoke                    # live: Models API + one recap in dev

The gate is the CI step that stands between a release config and production. Every
check is a plain function that returns (status, detail), so each one is testable.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from l10_platforms import FEATURES, PLATFORMS, adr_markdown, gaps, load_requirements, platform_model_id
from l10_release import (
    LAB_DIR,
    LIFECYCLE,
    LOCK_FILE,
    MOVING_ALIASES,
    PROMPTS_DIR,
    ReleaseConfig,
    load_config,
    load_eval,
    load_lock,
    lock_prompt,
    prompt_path,
    prompt_sha,
    scan_for_secrets,
)

sys.path.insert(0, str(LAB_DIR.parent / "L2-weekly-recaps"))
from l2_costs import PRICES, project  # noqa: E402  (one price table, owned by L2)

OUT_DIR = LAB_DIR / "out"
REQUIREMENTS = LAB_DIR / "requirements.json"
DEFAULT_CONFIG = LAB_DIR / "release.json"  # yours to fix; release-solution.json is the reference
GITIGNORE = LAB_DIR.parent / ".gitignore"
RETIREMENT_WARNING_DAYS = 90
US_ONLY_MULTIPLIER = 1.1

PASS, WARN, FAIL, TODO = "pass", "warn", "FAIL", "todo"


@dataclass
class Context:
    """Everything a check may look at. Tests build one pointing at temp files."""

    config: ReleaseConfig
    today: date
    lab_dir: Path = LAB_DIR
    prompts_dir: Path = PROMPTS_DIR
    lock_file: Path = LOCK_FILE
    requirements: Path = REQUIREMENTS
    gitignore: Path = GITIGNORE


Result = tuple[str, str]


# --------------------------------------------------------------------------- #
# The checks
# --------------------------------------------------------------------------- #


def check_model_pinned(ctx: Context) -> Result:
    # TODO 1: FAIL if ctx.config.model is in MOVING_ALIASES (say which snapshot it points at today),
    #   FAIL if it's not in LIFECYCLE, otherwise PASS.
    return TODO, "write check_model_pinned"


def check_lifecycle(ctx: Context) -> Result:
    # TODO 2: look up LIFECYCLE (resolve an alias through MOVING_ALIASES first).
    #   retired -> FAIL; deprecated -> FAIL with the days left and the replacement;
    #   active but retires within RETIREMENT_WARNING_DAYS of ctx.today -> WARN; else PASS.
    return TODO, "write check_lifecycle"


def check_prompt_locked(ctx: Context) -> Result:
    # TODO 3: lock = load_lock(ctx.lock_file).
    #   FAIL if any locked prompt's file no longer matches its hash (edited in place).
    #   FAIL if ctx.config.prompt has no file, or isn't in the lock yet (not released). Else PASS.
    return TODO, "write check_prompt_locked"


def check_eval(ctx: Context) -> Result:
    # TODO 4: load_eval(ctx.lab_dir / ctx.config.eval_run) and the baseline_run.
    #   FAIL if the eval's (model, prompt) differs from the release's: you'd ship something untested.
    #   FAIL on any regression: a case that passed in the baseline and fails now.
    #   FAIL below the 90% success criterion. Else PASS with both pass rates.
    return TODO, "write check_eval"


def check_platform(ctx: Context) -> Result:
    # TODO 5: req = load_requirements(ctx.requirements); FAIL with gaps(platform, req) if any.
    #   Also FAIL when the work isn't interactive but ctx.config.batch is off. Else PASS.
    return TODO, "write check_platform"


def weekly_cost(config: ReleaseConfig) -> float:
    v = config.volume
    return project(
        config.model,
        requests=v.requests_per_week,
        shared=v.shared_tokens,
        unique=v.unique_tokens,
        output=v.output_tokens,
        batch=config.batch,
        cache="1h" if config.batch else "5m",
        hit_rate=v.batch_hit_rate if config.batch else 1.0,
    )


def check_budget(ctx: Context) -> Result:
    if ctx.config.model not in PRICES:
        return FAIL, f"no price for {ctx.config.model}; can't show the release fits the budget"
    req = load_requirements(ctx.requirements)
    # inference_geo="us" costs 1.1x on every token category.
    geo = US_ONLY_MULTIPLIER if req.us_only and FEATURES["inference_geo"].get(ctx.config.platform) else 1.0
    usd = weekly_cost(ctx.config) * geo
    status = PASS if usd <= ctx.config.weekly_budget_usd else FAIL
    return status, f"projected ${usd:.4f}/week against a budget of ${ctx.config.weekly_budget_usd:.2f}"


def check_secrets(ctx: Context) -> Result:
    hits = scan_for_secrets(ctx.lab_dir)
    if hits:
        return FAIL, f"key-shaped strings in {', '.join(hits)}: revoke the key, then remove it"
    ignored = ctx.gitignore.read_text().splitlines() if ctx.gitignore.exists() else []
    if ".env" not in ignored:
        return FAIL, ".env is not in .gitignore"
    return PASS, "no keys in the lab files; .env is git-ignored; the client reads credentials from the environment"


CHECKS: list[tuple[str, Callable[[Context], Result]]] = [
    ("Model pinned", check_model_pinned),
    ("Model lifecycle", check_lifecycle),
    ("Prompt version", check_prompt_locked),
    ("Eval gate", check_eval),
    ("Platform fit", check_platform),
    ("Budget", check_budget),
    ("Secrets", check_secrets),
]


def run_gate(ctx: Context) -> list[tuple[str, str, str]]:
    return [(name, *check(ctx)) for name, check in CHECKS]


# --------------------------------------------------------------------------- #
# Commands
# --------------------------------------------------------------------------- #


def gate(config_path: Path, today: date) -> int:
    config = load_config(config_path)
    print(f"== Release gate: {config.release} ({config.environment}) from {config_path.name}, {today}\n")
    results = run_gate(Context(config=config, today=today))
    for name, status, detail in results:
        mark = {PASS: "ok  ", WARN: "warn", FAIL: "FAIL", TODO: "todo"}[status]
        print(f"[{mark}] {name:<16} {detail}")
    failed = sum(status in (FAIL, TODO) for _, status, _ in results)
    print(f"\n{'BLOCKED' if failed else 'READY TO SHIP'}: {failed} failing check(s)")
    return 1 if failed else 0


def adr() -> None:
    req = load_requirements(REQUIREMENTS)
    # TODO 6: run gaps() for each platform in PLATFORMS and decide. Then fill in the decision,
    #   a rationale that names the constraint each rejected option fails, and the consequences
    #   (auth, client, model ids, cost, when to revisit).
    text = adr_markdown(req, decision="claude-api", rationale="TODO: why this platform.", consequences=["TODO"])
    OUT_DIR.mkdir(exist_ok=True)
    path = OUT_DIR / "ADR-001-platform.md"
    path.write_text(text)
    print(text)
    print(f"Saved to {path}")


def smoke(config_path: Path) -> None:
    """Live check in the DEV environment, with the release's exact model and prompt."""
    from l2_recaps import box_score

    from gridiron.client import client

    config = load_config(config_path)

    # Models API: does the pinned id exist, what are its limits, and what is its lifecycle
    # right now? The gate's LIFECYCLE table is an offline copy; the API is the live source.
    info = client.models.retrieve(config.model)
    print(f"Models API: {info.id} ({info.display_name}), max input {info.max_input_tokens}, max output {info.max_tokens}")
    print(f"Lifecycle: {info.lifecycle}, deprecated_at {info.deprecated_at}, retires_at {info.retires_at}")
    known = LIFECYCLE.get(config.model)
    if known is None or known.state != info.lifecycle:
        print(f"WARNING: LIFECYCLE says {known.state if known else 'nothing'}; update the table before the next gate run")
    print(f"On {PLATFORMS[config.platform]['name']} the id is {platform_model_id(config.platform, config.model)}")

    prompt = prompt_path(config.prompt).read_text()
    message = client.messages.create(
        model=config.model,
        max_tokens=config.max_tokens,
        output_config={"effort": config.effort},
        system=prompt,
        messages=[{"role": "user", "content": box_score("POR", 3)}],
    )
    if message.stop_reason in ("max_tokens", "refusal"):
        raise SystemExit(f"Smoke test failed: stop_reason={message.stop_reason}")
    # One structured log line per request: enough to trace any output back to its release.
    log = {
        "release": config.release,
        "model": message.model,
        "prompt": config.prompt,
        "prompt_sha": prompt_sha(prompt)[:12],
        "request_id": message._request_id,
        "input_tokens": message.usage.input_tokens,
        "output_tokens": message.usage.output_tokens,
    }
    print(json.dumps(log))
    print("".join(b.text for b in message.content if b.type == "text"))


def main() -> None:
    parser = argparse.ArgumentParser(description="L10 ship it")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("adr")
    g = sub.add_parser("gate")
    g.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    g.add_argument("--today", type=date.fromisoformat, default=date.today())
    lk = sub.add_parser("lock")
    lk.add_argument("ref")
    s = sub.add_parser("smoke")
    s.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()

    if args.command == "adr":
        adr()
    elif args.command == "gate":
        raise SystemExit(gate(args.config, args.today))
    elif args.command == "lock":
        print(f"{args.ref} locked at {lock_prompt(args.ref)[:12]}")
    else:
        smoke(args.config)


if __name__ == "__main__":
    main()
