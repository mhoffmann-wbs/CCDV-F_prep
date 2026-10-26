"""L10 platforms: where Claude can run, what each platform offers, and the decision record.

Feature availability checked 2026-10-26 against the platform docs. It changes:
re-check the platform pages before you rely on a row.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel

Platform = Literal["claude-api", "claude-platform-aws", "bedrock", "vertex"]

PLATFORMS: dict[str, dict[str, str]] = {
    "claude-api": {
        "name": "Claude API (first party)",
        "operator": "Anthropic",
        "billing": "anthropic",
        "client": "anthropic.Anthropic",
        "auth": "API key, ant auth login profile, or Workload Identity Federation",
    },
    "claude-platform-aws": {
        "name": "Claude Platform on AWS",
        "operator": "Anthropic",
        "billing": "aws",
        "client": "anthropic.AnthropicAWS",
        "auth": "AWS IAM (SigV4)",
    },
    "bedrock": {
        "name": "Amazon Bedrock",
        "operator": "AWS",
        "billing": "aws",
        "client": "anthropic.AnthropicBedrockMantle",
        "auth": "AWS IAM",
    },
    "vertex": {
        "name": "Vertex AI (Google managed)",
        "operator": "Google",
        "billing": "gcp",
        "client": "anthropic.AnthropicVertex",
        "auth": "Google Cloud ADC",
    },
}

# True = available (GA or beta), False = not available on that platform's Claude API surface.
FEATURES: dict[str, dict[str, bool]] = {
    "messages_streaming_tools": {"claude-api": True, "claude-platform-aws": True, "bedrock": True, "vertex": True},
    "structured_outputs": {"claude-api": True, "claude-platform-aws": True, "bedrock": True, "vertex": True},
    "prompt_caching": {"claude-api": True, "claude-platform-aws": True, "bedrock": True, "vertex": True},
    "message_batches": {"claude-api": True, "claude-platform-aws": True, "bedrock": False, "vertex": False},
    "files_api": {"claude-api": True, "claude-platform-aws": True, "bedrock": False, "vertex": False},
    "models_api": {"claude-api": True, "claude-platform-aws": True, "bedrock": False, "vertex": False},
    "inference_geo": {"claude-api": True, "claude-platform-aws": True, "bedrock": False, "vertex": False},
    "mcp_connector": {"claude-api": True, "claude-platform-aws": True, "bedrock": False, "vertex": False},
}

# How each platform keeps inference in the US. Bedrock and Vertex have no inference_geo
# parameter; residency comes from the region (and, on Bedrock, the inference profile).
US_RESIDENCY: dict[str, str] = {
    "claude-api": 'inference_geo="us" on each request (1.1x price)',
    "claude-platform-aws": 'inference_geo="us" on each request (1.1x price)',
    "bedrock": "a US region, with an inference profile that keeps traffic in the US",
    "vertex": 'a US region or the "us" multi-region',
}


def platform_model_id(platform: str, model: str) -> str:
    """The same model has a platform-specific id on Bedrock; elsewhere it's the bare id."""
    return f"anthropic.{model}" if platform == "bedrock" else model


class Requirements(BaseModel):
    title: str
    goal: str
    functional: list[str]
    success_criteria: list[str]
    billing: Literal["anthropic", "aws", "gcp", "any"]
    us_only: bool
    interactive: bool
    weekly_budget_usd: float
    features: list[str]


def load_requirements(path: Path) -> Requirements:
    return Requirements.model_validate_json(path.read_text())


def gaps(platform: str, req: Requirements) -> list[str]:
    """Hard requirements this platform doesn't meet (empty = it qualifies)."""
    found = []
    billing = PLATFORMS[platform]["billing"]
    if req.billing != "any" and billing != req.billing:
        found.append(f"billed through {billing}, required: {req.billing}")
    for feature in req.features:
        if feature not in FEATURES:
            raise ValueError(f"unknown feature {feature!r}; known: {', '.join(FEATURES)}")
        if not FEATURES[feature][platform]:
            found.append(f"no {feature}")
    return found


def adr_markdown(req: Requirements, decision: str, rationale: str, consequences: list[str]) -> str:
    """An architecture decision record: context, options with their gaps, decision, consequences."""
    rows = []
    for pid, p in PLATFORMS.items():
        g = gaps(pid, req)
        residency = US_RESIDENCY[pid] if req.us_only else "n/a"
        rows.append(f"| {p['name']} | {p['operator']} | {p['billing']} | {residency} | {'; '.join(g) or 'meets all'} |")
    return "\n".join(
        [
            f"# ADR-001: Platform for {req.title}",
            "",
            "Status: accepted",
            "",
            "## Context",
            "",
            req.goal,
            "",
            "Functional requirements:",
            *[f"- {f}" for f in req.functional],
            "",
            "Success criteria:",
            *[f"- {s}" for s in req.success_criteria],
            "",
            f"Constraints: billing through **{req.billing}**, US-only inference: **{req.us_only}**, "
            f"interactive: **{req.interactive}**, budget **${req.weekly_budget_usd:.2f}/week**. "
            f"Required API features: {', '.join(req.features)}.",
            "",
            "## Options",
            "",
            "| Platform | Operated by | Billing | US-only inference | Gaps |",
            "|---|---|---|---|---|",
            *rows,
            "",
            "## Decision",
            "",
            f"**{PLATFORMS[decision]['name']}.** {rationale}",
            "",
            "## Consequences",
            "",
            *[f"- {c}" for c in consequences],
            "",
        ]
    )
