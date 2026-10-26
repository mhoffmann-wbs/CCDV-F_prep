"""Offline tests for the tool loop: a scripted stand-in for client.messages.create. No API calls."""

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest
from l4_league import LineupStore
from test_l4_league import GOOD

_spec = importlib.util.spec_from_file_location("l4_solution", Path(__file__).with_name("solution.py"))
solution = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(solution)


def call(id, name, **input):
    return SimpleNamespace(type="tool_use", id=id, name=name, input=input)


def text(t):
    return SimpleNamespace(type="text", text=t)


def reply(*content, stop="tool_use"):
    return SimpleNamespace(content=list(content), stop_reason=stop, stop_details=None)


class Script:
    """Returns the scripted responses in order and records every request."""

    def __init__(self, *responses):
        self.responses = list(responses)
        self.requests = []

    def __call__(self, **kwargs):
        # Snapshot: the loop keeps appending to the same list.
        self.requests.append({**kwargs, "messages": list(kwargs["messages"])})
        return self.responses.pop(0)


def test_parallel_calls_go_back_in_one_user_message(tmp_path):
    script = Script(
        reply(
            call("t1", "get_player_stats", player_ids=["POR-QB1"], detail="summary"),
            call("t2", "get_injury_status", player_ids=["POR-QB1"]),
        ),
        reply(text("Start Holloway."), stop="end_turn"),
    )
    answer, messages = solution.run_assistant(
        "Should I start Holloway?", create=script, approve=lambda _: True, store=LineupStore(tmp_path / "l.json")
    )
    assert answer == "Start Holloway."
    assert [m["role"] for m in messages] == ["user", "assistant", "user", "assistant"]
    results = messages[2]["content"]
    assert [r["tool_use_id"] for r in results] == ["t1", "t2"]  # one message, call order kept
    assert all(r["type"] == "tool_result" for r in results)
    # The second request carries the assistant turn exactly as returned.
    assert script.requests[1]["messages"][1]["content"] is messages[1]["content"]
    assert script.requests[0]["tools"] and script.requests[0]["system"]


def test_errors_are_returned_so_claude_can_retry(tmp_path):
    store = LineupStore(tmp_path / "l.json")
    script = Script(
        reply(call("t1", "set_lineup", week=4, lineup=dict(GOOD, WR1="NSH-WR1"), rationale="x")),
        reply(call("t2", "set_lineup", week=4, lineup=GOOD, rationale="Healthy starters.")),
        reply(text("Saved."), stop="end_turn"),
    )
    asked = []
    solution.run_assistant("Set it", create=script, approve=lambda p: asked.append(p) or True, store=store)
    first = script.requests[1]["messages"][-1]["content"][0]
    assert first["is_error"] is True and "ruled Out" in first["content"]
    assert len(asked) == 1  # only the valid lineup reached the human
    assert store.load()["lineup"] == GOOD


def test_turn_limit_stops_a_runaway_loop(tmp_path):
    looping = [reply(call(f"t{i}", "get_roster")) for i in range(3)]
    with pytest.raises(RuntimeError, match="3 turns"):
        solution.run_assistant(
            "x", create=Script(*looping), approve=lambda _: True, store=LineupStore(tmp_path / "l.json"), max_turns=3
        )


@pytest.mark.parametrize("stop", ["max_tokens", "refusal"])
def test_untrusted_stops_raise_before_any_tool_runs(tmp_path, stop):
    def boom(_):
        raise AssertionError("no tool may run")

    script = Script(reply(call("t1", "set_lineup", week=4, lineup=GOOD, rationale="x"), stop=stop))
    with pytest.raises(RuntimeError):
        solution.run_assistant("x", create=script, approve=boom, store=LineupStore(tmp_path / "l.json"))


def test_context_editing_keeps_set_lineup_and_recent_results():
    (edit,) = solution.CLEAR_OLD_RESULTS["edits"]
    assert edit["type"] == "clear_tool_uses_20250919"
    assert "set_lineup" in edit["exclude_tools"]
    assert edit["keep"]["value"] < edit["trigger"]["value"]
