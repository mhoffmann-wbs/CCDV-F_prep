"""L9 starter: pick'em evals with code graders and a calibrated LLM judge, plus triage.

Run from labs/ (each command is one step of the lab):
  uv run python L9-pickem-evals/starter.py triage                    # offline: your classify() on the incidents
  uv run python L9-pickem-evals/starter.py grade                     # offline: your number grader on 16 picks
  uv run python L9-pickem-evals/starter.py calibrate                 # your judge vs. 16 hand labels
  uv run python L9-pickem-evals/starter.py run --tier haiku          # 12 picks, code graders + judge

Fill in the numbered TODOs. The reference versions are in l9_errors.py, l9_cases.py and solution.py:
read them after you've tried, not before.
"""

from __future__ import annotations

import argparse
import re
from typing import Any

import anthropic

from gridiron.client import TIERS, client, log_usage
from l9_cases import PICK_SYSTEM, Case, JudgeVerdict, Pick, build_cases, calibration, grade_code, load_recorded, pick_messages
from l9_errors import (  # noqa: F401  (the actions your classify() returns)
    ALERT,
    FIX_ACCESS,
    FIX_REQUEST,
    OK,
    RAISE_LIMIT,
    REFUSAL,
    RETRY,
    RETRY_AFTER,
    SHRINK,
    STREAM,
    Failure,
    failure_from_exception,
    load_traces,
)
from l5_data import stats_text  # noqa: F401  (on the path via l9_cases)

api = client.with_options(max_retries=4)


# --------------------------------------------------------------------------- #
# Step 2: classify failures
# --------------------------------------------------------------------------- #


def classify(f: Failure) -> str:
    # TODO 1: return the action for each outcome. Order matters:
    #   status 0 (no response) -> RETRY
    #   429 -> RETRY_AFTER if f.retry_after is set, else ALERT (a spend cap keeps failing)
    #   500, 529 -> RETRY;  504 -> STREAM;  413 -> SHRINK;  401/403/404 -> FIX_ACCESS
    #   any other 4xx -> FIX_REQUEST (the same body fails every time)
    #   200 with stop_reason max_tokens -> RAISE_LIMIT, refusal -> REFUSAL, else OK
    return OK


def run_triage() -> None:
    for r in load_traces():
        error = r.get("error") or {}
        f = Failure(r["status"], error.get("type"), r.get("retry_after"), r.get("stop_reason"))
        print(f"{r['id']} {r['status']} {error.get('type') or r.get('stop_reason')!s:<22} -> {classify(f)}")
    print("\nCompare with: uv run python L9-pickem-evals/solution.py triage")
    print("That also separates integration bugs from model output, using the tool results in each trace.")


# --------------------------------------------------------------------------- #
# Step 3: a code grader for numbers
# --------------------------------------------------------------------------- #

NUMBER = re.compile(r"(?<![\w.-])\d+(?:\.\d+)?(?![\w-])")


def ungrounded_numbers(pick: Pick) -> list[str]:
    """Numbers in a factor's claim that don't appear in that player's data."""
    # TODO 2: for each factor, collect the allowed numbers: NUMBER.findall(stats_text([player_id], "full"))
    #   as floats, plus the week numbers 1, 2 and 3. Every number in the claim must be within 0.05 of an
    #   allowed one, or equal to one rounded to a whole number (23.83 -> 24). Report the others as
    #   f"{player_id}: {number} is not in his stats".
    return []


def run_grade() -> None:
    cases = {c.id: c for c in build_cases()}
    for r in load_recorded():
        mine = ungrounded_numbers(r.pick)
        reference = grade_code(r.pick, cases[r.case])
        print(f"{r.id} human={'grounded' if r.human_grounded else 'NOT grounded':<13} yours={mine} reference={reference}")
    print("\nWhich ungrounded picks pass every code check? Those are the judge's job.")


# --------------------------------------------------------------------------- #
# Step 4: the judge, calibrated against hand labels
# --------------------------------------------------------------------------- #

# TODO 3: this judge prompt is deliberately weak. Rewrite it as a rubric: one question (is every
#   claim supported by the data?), what counts as supported (stated, rounding, simple comparisons)
#   and what doesn't (records, streaks, head-to-head history, weather, quotes, health beyond the
#   injury report), and "whether the pick is wise doesn't matter". Re-run calibrate after each change.
JUDGE_SYSTEM = "You review football predictions. Say whether the pick is good."


def judge_messages(case: Case, pick: Pick) -> list[dict[str, Any]]:
    return [
        {
            "role": "user",
            "content": f"<data>\n{case.data}\n</data>\n\n<pick>\n{pick.model_dump_json(indent=2)}\n</pick>",
        }
    ]


def parse(model: str, system: str, messages: list[dict[str, Any]], schema: type, label: str) -> Any:
    response = api.messages.parse(
        model=model, max_tokens=16000, output_config={"effort": "low"}, system=system, messages=messages, output_format=schema
    )
    log_usage(f"{label} {response._request_id}", response.usage)
    if response.stop_reason in ("refusal", "max_tokens") or response.parsed_output is None:
        raise RuntimeError(f"unusable response: stop_reason={response.stop_reason}")
    return response.parsed_output


def run_calibrate(judge_model: str) -> None:
    cases = {c.id: c for c in build_cases()}
    human, verdicts = [], []
    for r in load_recorded():
        verdict = parse(judge_model, JUDGE_SYSTEM, judge_messages(cases[r.case], r.pick), JudgeVerdict, "judge")
        human.append(r.human_grounded)
        verdicts.append(verdict.grounded)
        if verdict.grounded != r.human_grounded:
            print(f"  disagree on {r.id}: judge {verdict.grounded}, human {r.human_grounded} ({r.note})")
    m = calibration(human, verdicts)
    print(f"\nagreement {m['agreement']:.0%}, false passes {m['false_pass_rate']:.0%}, false fails {m['false_fail_rate']:.0%}")


# --------------------------------------------------------------------------- #
# Step 5: the eval run
# --------------------------------------------------------------------------- #


def run_eval(model: str, judge_model: str) -> None:
    passed = graded = 0
    for case in build_cases():
        # TODO 4: wrap this call in try/except anthropic.APIError. On an error, print the case,
        #   the exception type and classify(failure_from_exception(e)), and `continue`: an outage
        #   is not a wrong pick, so it must not count against the model's score.
        pick = parse(model, PICK_SYSTEM, pick_messages(case), Pick, f"pick {case.id}")
        problems = grade_code(pick, case)
        verdict = parse(judge_model, JUDGE_SYSTEM, judge_messages(case, pick), JudgeVerdict, "judge")
        graded += 1
        passed += not problems and verdict.grounded
        print(f"{case.id}: {pick.winner} {pick.confidence} | code {problems or 'ok'} | judge {verdict.unsupported_claims or 'ok'}")
    print(f"\n{model}: {passed}/{graded} picks pass both graders")
    _ = anthropic  # used by TODO 4


def main() -> None:
    parser = argparse.ArgumentParser(description="L9 pick'em evals and debugging (starter)")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("triage")
    sub.add_parser("grade")
    c = sub.add_parser("calibrate")
    c.add_argument("--judge", choices=TIERS, default="sonnet")
    r = sub.add_parser("run")
    r.add_argument("--tier", choices=TIERS, default="haiku")
    r.add_argument("--judge", choices=TIERS, default="sonnet")
    args = parser.parse_args()
    if args.command == "triage":
        run_triage()
    elif args.command == "grade":
        run_grade()
    elif args.command == "calibrate":
        run_calibrate(TIERS[args.judge])
    else:
        run_eval(TIERS[args.tier], TIERS[args.judge])


if __name__ == "__main__":
    main()
