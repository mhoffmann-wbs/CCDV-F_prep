"""L9 debugging: classify a failure into the action it needs, and triage a recorded trace.

The decisive questions, in order:
  1. Did the request fail (non-2xx), or did a 200 come back with a stop_reason you can't use?
  2. For a failed request: will the same request ever succeed if you just wait?
  3. For a bad answer: was the input Claude saw correct? If not, it's an integration bug,
     and no prompt change will fix it.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import anthropic

LAB_DIR = Path(__file__).resolve().parent
TRACES = LAB_DIR / "traces.jsonl"

# Actions
RETRY = "retry with backoff"
RETRY_AFTER = "wait for retry-after, then retry"
FIX_REQUEST = "fix the request; the same body fails every time"
FIX_ACCESS = "fix the key, permissions or model id"
SHRINK = "shrink or split the input"
STREAM = "stream, or move the job to Batches"
ALERT = "stop and alert: a spend cap, waiting won't help"
RAISE_LIMIT = "raise max_tokens; don't parse the partial output"
REFUSAL = "read stop_details; don't retry blindly"
FIX_DATA = "fix the data feed or tool; the model answered what it was given"
FIX_PROMPT = "fix the prompt, examples or validation; the input was right"
OK = "nothing to do"


@dataclass(frozen=True)
class Failure:
    """The facts you need to classify any outcome, whether it raised or returned."""

    status: int  # HTTP status; 0 for a connection failure
    error_type: str | None = None  # error.type from the body, e.g. "rate_limit_error"
    retry_after: float | None = None  # seconds, from the retry-after header
    stop_reason: str | None = None  # for 200s


def classify(f: Failure) -> str:
    if f.status == 0:
        return RETRY  # network or timeout before a response
    if f.status == 429:
        # A rate limit says when to come back. A monthly spend cap doesn't, and keeps failing.
        return RETRY_AFTER if f.retry_after is not None else ALERT
    if f.status in (500, 529) or f.error_type in ("api_error", "overloaded_error"):
        return RETRY
    if f.status == 504:
        return STREAM
    if f.status == 413:
        return SHRINK
    if f.status in (401, 403, 404):
        return FIX_ACCESS
    if 400 <= f.status < 500:
        return FIX_REQUEST
    if f.stop_reason == "max_tokens":
        return RAISE_LIMIT
    if f.stop_reason == "refusal":
        return REFUSAL
    return OK


def failure_from_exception(e: anthropic.APIError) -> Failure:
    """Map an SDK exception to a Failure. Typed exceptions, never string matching."""
    if isinstance(e, anthropic.APIStatusError):
        body = e.body if isinstance(e.body, dict) else {}
        header = e.response.headers.get("retry-after")
        return Failure(
            status=e.status_code,
            error_type=(body.get("error") or {}).get("type"),
            retry_after=float(header) if header else None,
        )
    return Failure(status=0)  # APIConnectionError, APITimeoutError


# --------------------------------------------------------------------------- #
# Trace triage: one recorded call per line in traces.jsonl.
# --------------------------------------------------------------------------- #


def load_traces(path: Path = TRACES) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _stale_tool_results(record: dict[str, Any]) -> list[str]:
    """Tool results whose data is older than the trace says it should be."""
    fresh_from = record.get("data_fresh_from")
    if not fresh_from:
        return []
    cutoff = date.fromisoformat(fresh_from)
    return [
        f"{c['name']} returned data from {c['data_as_of']} (expected {fresh_from} or later)"
        for c in record.get("tool_calls", [])
        if c.get("data_as_of") and date.fromisoformat(c["data_as_of"]) < cutoff
    ]


def triage(record: dict[str, Any]) -> tuple[str, str, str]:
    """(layer, action, evidence) for one trace record."""
    error = record.get("error") or {}
    failure = Failure(
        status=record["status"],
        error_type=error.get("type"),
        retry_after=record.get("retry_after"),
        stop_reason=record.get("stop_reason"),
    )
    action = classify(failure)
    if record["status"] != 200:
        layer = {RETRY: "transient", RETRY_AFTER: "transient", ALERT: "account"}.get(action, "integration")
        return layer, action, f"{record['status']} {error.get('type')}: {error.get('message', '')}"
    if action != OK:
        return "integration", action, f"200 with stop_reason={failure.stop_reason}"
    if stale := _stale_tool_results(record):
        return "integration", FIX_DATA, "; ".join(stale)
    if record.get("grader_problems"):
        return "model output", FIX_PROMPT, "; ".join(record["grader_problems"])
    return "none", OK, "request and output both check out"
