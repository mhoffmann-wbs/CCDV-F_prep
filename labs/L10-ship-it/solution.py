"""L10 reference solution: ship the weekly recap job.

Run from labs/:
  uv run python L10-ship-it/solution.py adr                      # write the platform decision record
  uv run python L10-ship-it/solution.py gate --config L10-ship-it/release.json            # today's prod: red
  uv run python L10-ship-it/solution.py lock recap@v2            # record a prompt version as released
  uv run python L10-ship-it/solution.py gate                     # the fixed release: green once v2 is locked
  uv run python L10-ship-it/solution.py smoke                    # live: Models API + one recap in dev

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
DEFAULT_CONFIG = LAB_DIR / "release-solution.json"
GITIGNORE = LAB_DIR.parent / ".gitignore"
RETIREMENT_WARNING_DAYS = 90
US_ONLY_MULTIPLIER = 1.1

PASS, WARN, FAIL = "pass", "warn", "FAIL"


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
    model = ctx.config.model
    if model in MOVING_ALIASES:
        target = MOVING_ALIASES[model]
        hint = f" (today it points at {target}; pin that, or move to a current model)" if target else ""
        return FAIL, f"{model} is an alias that can move to a different model{hint}"
    if model not in LIFECYCLE:
        return FAIL, f"{model} is not in the lifecycle table; check the id and its status before shipping"
    return PASS, f"{model} is a fixed snapshot"


def check_lifecycle(ctx: Context) -> Result:
    info = LIFECYCLE.get(MOVING_ALIASES.get(ctx.config.model) or ctx.config.model)
    if info is None:
        return FAIL, "unknown model"
    if info.state == "retired":
        return FAIL, f"retired on {info.retires}; requests fail. Use {info.replacement}"
    if info.state == "deprecated":
        days = (info.retires - ctx.today).days
        return FAIL, f"deprecated, retires {info.retires} ({days} days). Migrate to {info.replacement}"
    if info.retires and (info.retires - ctx.today).days <= RETIREMENT_WARNING_DAYS:
        return WARN, f"active, but may be retired from {info.retires}; plan the next migration"
    return PASS, f"active, retires no sooner than {info.retires}"


def check_prompt_locked(ctx: Context) -> Result:
    lock = load_lock(ctx.lock_file)
    edited = []
    for ref, sha in lock.items():
        path = prompt_path(ref, ctx.prompts_dir)
        if path.exists() and prompt_sha(path.read_text()) != sha:
            edited.append(ref)
    if edited:
        return FAIL, f"released prompt(s) edited in place: {', '.join(edited)}. Revert, and put the change in a new version"
    ref = ctx.config.prompt
    if not prompt_path(ref, ctx.prompts_dir).exists():
        return FAIL, f"{ref} has no file in prompts/"
    if ref not in lock:
        return FAIL, f"{ref} is not released yet: run `lock {ref}` after review"
    return PASS, f"{ref} matches its released hash {lock[ref][:12]}"


def check_eval(ctx: Context) -> Result:
    run = load_eval(ctx.lab_dir / ctx.config.eval_run)
    baseline = load_eval(ctx.lab_dir / ctx.config.baseline_run)
    if (run.model, run.prompt) != (ctx.config.model, ctx.config.prompt):
        return FAIL, f"the eval ran {run.model} + {run.prompt}, but the release ships {ctx.config.model} + {ctx.config.prompt}"
    before = {c.id: c.passed for c in baseline.cases}
    regressions = [f"{c.id} ({c.note})" for c in run.cases if before.get(c.id) and not c.passed]
    summary = f"{run.pass_rate:.0%} vs baseline {baseline.pass_rate:.0%}"
    if regressions:
        return FAIL, f"{summary}; regressions: {', '.join(regressions)}"
    if run.pass_rate < 0.9:
        return FAIL, f"{summary}; below the 90% success criterion"
    return PASS, f"{summary}, no regressions"


def check_platform(ctx: Context) -> Result:
    req = load_requirements(ctx.requirements)
    if ctx.config.platform not in PLATFORMS:
        return FAIL, f"unknown platform {ctx.config.platform!r}"
    found = gaps(ctx.config.platform, req)
    if found:
        return FAIL, f"{PLATFORMS[ctx.config.platform]['name']}: {'; '.join(found)}"
    if not req.interactive and not ctx.config.batch:
        return FAIL, "nobody waits on this job, but batch is off: you pay twice the price for latency no one needs"
    return PASS, f"{PLATFORMS[ctx.config.platform]['name']} meets every hard requirement"


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
        mark = {PASS: "ok  ", WARN: "warn", FAIL: "FAIL"}[status]
        print(f"[{mark}] {name:<16} {detail}")
    failed = sum(status == FAIL for _, status, _ in results)
    print(f"\n{'BLOCKED' if failed else 'READY TO SHIP'}: {failed} failing check(s)")
    return 1 if failed else 0


def adr() -> None:
    req = load_requirements(REQUIREMENTS)
    text = adr_markdown(
        req,
        decision="claude-platform-aws",
        rationale=(
            "It is the only option that bills through AWS and offers the Message Batches API. Anthropic "
            "operates it, so features arrive with the same-day parity as the Claude API, and inference_geo "
            'set to "us" keeps processing in the US. Bedrock also bills through AWS, but it has no Message '
            "Batches API (its own batch inference jobs are a different interface), so we would pay "
            "realtime prices for work nobody waits on."
        ),
        consequences=[
            "Authentication moves to AWS IAM (SigV4); no Anthropic API key exists in production.",
            "The client becomes anthropic.AnthropicAWS; model ids stay bare (claude-sonnet-5-5).",
            'Every request sets inference_geo="us", which costs 1.1x. The budget check includes this margin.',
            "Lifecycle dates for Anthropic-operated platforms apply, so the deprecation table stays our reference.",
            "Revisit if the league office drops the AWS-billing constraint or needs a feature this platform lacks.",
        ],
    )
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
