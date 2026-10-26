import importlib.util
import sys
from pathlib import Path

from l9_cases import (
    Factor,
    JudgeVerdict,
    Pick,
    build_cases,
    calibration,
    grade_code,
    judge_messages,
    load_recorded,
    pick_messages,
)

_spec = importlib.util.spec_from_file_location("l9_solution", Path(__file__).with_name("solution.py"))
solution = importlib.util.module_from_spec(_spec)
sys.modules["l9_solution"] = solution
_spec.loader.exec_module(solution)

CASES = {c.id: c for c in build_cases()}


def test_one_case_per_scheduled_game_with_tagged_data():
    assert len(CASES) == 12
    case = CASES["w4-nsh-bal"]
    assert case.data.startswith("<matchup>Week 4: Nashville Night Owls (NSH) at Baltimore")
    assert "NSH-WR1 | Darius Kincaid | Out" in case.data
    assert "POR-" not in case.data  # only the two teams in this game
    assert pick_messages(case)[0]["content"].endswith("Pick the winner of this game.")


def test_code_graders_on_the_recorded_picks():
    flagged = {r.id: grade_code(r.pick, CASES[r.case]) for r in load_recorded()}
    assert {k for k, v in flagged.items() if v} == {"r07", "r08", "r09", "r10"}
    assert flagged["r07"] == ["NSH-WR3: 31.0 is not in his stats"]
    assert flagged["r08"] == ["cites NSH-WR1 (Out) as if he will play"]


def test_code_graders_miss_what_only_a_judge_can_see():
    # Ungrounded claims without numbers pass every code check; that's why the judge exists.
    judge_only = [r for r in load_recorded() if not r.human_grounded and not grade_code(r.pick, CASES[r.case])]
    assert {r.id for r in judge_only} == {"r11", "r12", "r13", "r14", "r16"}


def test_rounding_and_week_numbers_are_grounded_but_new_numbers_are_not():
    case = CASES["w5-sac-nsh"]

    def pick(claim):
        return Pick(winner="NSH", confidence=60, rationale="x",
                    key_factors=[Factor(player_id="NSH-RB2", claim=claim), Factor(player_id="NSH-QB1", claim="ok")])  # fmt: skip

    assert grade_code(pick("Trey Fairbanks averages 23.8, about 24, in week 3 he had 24.2."), case) == []
    assert grade_code(pick("Trey Fairbanks scored 40 in week 2."), case) == ["NSH-RB2: 40 is not in his stats"]


def test_structural_rules_are_checked_in_code():
    case = CASES["w1-sac-por"]
    bad = Pick(winner="NSH", confidence=101, rationale="x", key_factors=[Factor(player_id="XXX-QB9", claim="c")])
    assert grade_code(bad, case) == [
        "winner 'NSH' is not SAC or POR",
        "confidence 101 is outside 50-100",
        "1 key factors, expected 2-3",
        "unknown player id 'XXX-QB9'",
    ]


def test_judge_sees_data_then_pick_and_reasons_before_its_verdict():
    r = load_recorded()[0]
    content = judge_messages(CASES[r.case], r.pick)[0]["content"]
    assert content.index("<data>") < content.index("<pick>")
    assert list(JudgeVerdict.model_fields) == ["reasoning", "unsupported_claims", "grounded"]


def test_recorded_labels_are_balanced():
    labels = [r.human_grounded for r in load_recorded()]
    assert len(labels) == 16 and sum(labels) == 8


def test_calibration_metrics():
    human = [True, True, False, False, False]
    judge = [True, False, True, False, False]
    assert calibration(human, judge) == {
        "n": 5,
        "agreement": 0.6,
        "false_pass_rate": 1 / 3,
        "false_fail_rate": 0.5,
    }
