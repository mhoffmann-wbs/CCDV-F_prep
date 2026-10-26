"""L9 reference solution: pick'em evals with code graders and a calibrated LLM judge, plus triage.

Run from labs/ (each command is one step of the lab):
  uv run python L9-pickem-evals/solution.py triage                    # offline: classify the recorded incidents
  uv run python L9-pickem-evals/solution.py calibrate                 # judge vs. 16 hand labels
  uv run python L9-pickem-evals/solution.py calibrate --judge haiku   # a cheaper judge: does it agree as well?
  uv run python L9-pickem-evals/solution.py run --tier haiku          # 12 picks, code graders + judge
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import anthropic

from gridiron.client import TIERS, client, log_usage
from l9_cases import (
    JUDGE_SYSTEM,
    PICK_SYSTEM,
    Case,
    JudgeVerdict,
    Pick,
    build_cases,
    calibration,
    grade_code,
    judge_messages,
    load_recorded,
    pick_messages,
)
from l9_errors import classify, failure_from_exception, load_traces, triage

LAB_DIR = Path(__file__).resolve().parent
OUT_DIR = LAB_DIR / "out"
api = client.with_options(max_retries=4)  # 429/5xx/connection errors: backoff and retry, built in


class Unusable(Exception):
    """A response came back but can't be used (refusal, truncation, no parsed output)."""


def parse(model: str, system: str, messages: list[dict[str, Any]], schema: type, label: str) -> Any:
    response = api.messages.parse(
        model=model,
        max_tokens=16000,
        output_config={"effort": "low"},
        system=system,
        messages=messages,
        output_format=schema,
    )
    log_usage(f"{label} {response._request_id}", response.usage)
    if response.stop_reason in ("refusal", "max_tokens") or response.parsed_output is None:
        raise Unusable(f"stop_reason={response.stop_reason}")
    return response.parsed_output


def judge(case: Case, pick: Pick, model: str) -> JudgeVerdict:
    return parse(model, JUDGE_SYSTEM, judge_messages(case, pick), JudgeVerdict, "judge")


# --------------------------------------------------------------------------- #
# Step 2: triage (offline)
# --------------------------------------------------------------------------- #


def run_triage() -> None:
    for record in load_traces():
        layer, action, evidence = triage(record)
        print(f"{record['id']} {record['request_id']:<18} {layer:<13} -> {action}\n    {evidence}")


# --------------------------------------------------------------------------- #
# Step 4: calibrate the judge against the hand labels
# --------------------------------------------------------------------------- #


def run_calibrate(judge_model: str) -> None:
    cases = {c.id: c for c in build_cases()}
    human, verdicts, disagreements = [], [], []
    for r in load_recorded():
        verdict = judge(cases[r.case], r.pick, judge_model)
        human.append(r.human_grounded)
        verdicts.append(verdict.grounded)
        if verdict.grounded != r.human_grounded:
            disagreements.append(f"{r.id}: judge {verdict.grounded}, human {r.human_grounded} ({r.note})\n"
                                 f"    judge said: {verdict.reasoning[:300]}")  # fmt: skip
    m = calibration(human, verdicts)
    print(f"\nJudge {judge_model} on {m['n']} labelled picks: agreement {m['agreement']:.0%}, "
          f"false passes {m['false_pass_rate']:.0%}, false fails {m['false_fail_rate']:.0%}")  # fmt: skip
    for d in disagreements:
        print(f"  - {d}")


# --------------------------------------------------------------------------- #
# Step 5: the eval run
# --------------------------------------------------------------------------- #


def run_eval(model: str, judge_model: str) -> None:
    rows, results = [], []
    for case in build_cases():
        try:
            pick = parse(model, PICK_SYSTEM, pick_messages(case), Pick, f"pick {case.id}")
        except anthropic.APIError as e:
            # An infrastructure failure is not a model failure: record it separately.
            action = classify(failure_from_exception(e))
            rows.append(f"| {case.id} | error | | | {type(e).__name__}: {action} |")
            results.append({"case": case.id, "error": type(e).__name__, "action": action})
            continue
        except Unusable as e:
            rows.append(f"| {case.id} | unusable | | | {e} |")
            results.append({"case": case.id, "unusable": str(e)})
            continue
        problems = grade_code(pick, case)
        verdict = judge(case, pick, judge_model)
        passed = not problems and verdict.grounded
        detail = "; ".join(problems + verdict.unsupported_claims)[:120]
        rows.append(f"| {case.id} | {pick.winner} {pick.confidence} | {'ok' if not problems else 'FAIL'} | "
                    f"{'ok' if verdict.grounded else 'FAIL'} | {detail} |")  # fmt: skip
        results.append({"case": case.id, "pick": pick.model_dump(), "code_problems": problems,
                        "judge": verdict.model_dump(), "passed": passed})  # fmt: skip

    graded = [r for r in results if "passed" in r]
    print("\n| case | pick | code | judge | problems |\n|---|---|---|---|---|")
    print("\n".join(rows))
    if graded:
        print(f"\n{model}: {sum(r['passed'] for r in graded)}/{len(graded)} picks pass both graders; "
              f"{len(results) - len(graded)} not graded (errors or unusable responses)")  # fmt: skip
    OUT_DIR.mkdir(exist_ok=True)
    path = OUT_DIR / f"eval-{model}.json"
    path.write_text(json.dumps(results, indent=2) + "\n")
    print(f"Saved to {path}. Keep it: the next prompt or model change is compared against this run.")


def main() -> None:
    parser = argparse.ArgumentParser(description="L9 pick'em evals and debugging")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("triage")
    c = sub.add_parser("calibrate")
    c.add_argument("--judge", choices=TIERS, default="sonnet")
    r = sub.add_parser("run")
    r.add_argument("--tier", choices=TIERS, default="haiku")
    r.add_argument("--judge", choices=TIERS, default="sonnet")
    args = parser.parse_args()
    if args.command == "triage":
        run_triage()
    elif args.command == "calibrate":
        run_calibrate(TIERS[args.judge])
    else:
        run_eval(TIERS[args.tier], TIERS[args.judge])


if __name__ == "__main__":
    main()
