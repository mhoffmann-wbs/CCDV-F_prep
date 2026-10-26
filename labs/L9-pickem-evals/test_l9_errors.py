from types import SimpleNamespace

import anthropic
import pytest
from l9_errors import (
    ALERT,
    FIX_ACCESS,
    FIX_DATA,
    FIX_PROMPT,
    FIX_REQUEST,
    OK,
    RAISE_LIMIT,
    REFUSAL,
    RETRY,
    RETRY_AFTER,
    SHRINK,
    STREAM,
    Failure,
    classify,
    failure_from_exception,
    load_traces,
    triage,
)


@pytest.mark.parametrize(
    ("failure", "action"),
    [
        (Failure(0), RETRY),
        (Failure(529, "overloaded_error"), RETRY),
        (Failure(500, "api_error"), RETRY),
        (Failure(429, "rate_limit_error", retry_after=20), RETRY_AFTER),
        (Failure(429, "rate_limit_error"), ALERT),  # a spend cap: no retry-after, keeps failing
        (Failure(400, "invalid_request_error"), FIX_REQUEST),
        (Failure(401, "authentication_error"), FIX_ACCESS),
        (Failure(404, "not_found_error"), FIX_ACCESS),
        (Failure(413, "request_too_large"), SHRINK),
        (Failure(504, "timeout_error"), STREAM),
        (Failure(200, stop_reason="max_tokens"), RAISE_LIMIT),
        (Failure(200, stop_reason="refusal"), REFUSAL),
        (Failure(200, stop_reason="end_turn"), OK),
    ],
)
def test_classify(failure, action):
    assert classify(failure) == action


def status_error(cls, status, error_type, headers):
    """A real SDK exception instance, without building an HTTP response."""
    e = cls.__new__(cls)
    e.status_code = status
    e.body = {"type": "error", "error": {"type": error_type, "message": "x"}}
    e.response = SimpleNamespace(headers=headers)
    return e


def test_failure_from_typed_exceptions():
    limited = status_error(anthropic.RateLimitError, 429, "rate_limit_error", {"retry-after": "20"})
    assert failure_from_exception(limited) == Failure(429, "rate_limit_error", 20.0)
    capped = status_error(anthropic.RateLimitError, 429, "rate_limit_error", {})
    assert classify(failure_from_exception(capped)) == ALERT
    bad = status_error(anthropic.BadRequestError, 400, "invalid_request_error", {})
    assert classify(failure_from_exception(bad)) == FIX_REQUEST
    down = anthropic.APIConnectionError(message="connection reset", request=None)
    assert classify(failure_from_exception(down)) == RETRY


def test_triage_of_the_recorded_incidents():
    got = {r["id"]: triage(r)[:2] for r in load_traces()}
    assert got == {
        "t01": ("transient", RETRY),
        "t02": ("none", OK),
        "t03": ("integration", FIX_REQUEST),
        "t04": ("transient", RETRY_AFTER),
        "t05": ("integration", FIX_DATA),  # stale injury data: not the model's fault
        "t06": ("integration", RAISE_LIMIT),
        "t07": ("model output", FIX_PROMPT),  # fresh data, invented number
        "t08": ("integration", FIX_REQUEST),
        "t09": ("account", ALERT),
        "t10": ("integration", FIX_ACCESS),
    }


def test_stale_data_is_named_in_the_evidence():
    record = next(r for r in load_traces() if r["id"] == "t05")
    assert "2026-10-07" in triage(record)[2]
