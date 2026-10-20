"""One place for the client, model choice and usage logging, shared by all labs."""

from __future__ import annotations

import os
import sys

import anthropic

# The SDK resolves credentials from ANTHROPIC_API_KEY, ANTHROPIC_AUTH_TOKEN or an
# `ant auth login` profile. Never hard-code a key here or in any lab file.
client = anthropic.Anthropic()

# Default model for the labs. Override with MODEL=... to compare tiers.
MODEL = os.environ.get("MODEL") or "claude-opus-5-5"

# The three current tiers, for cost/quality comparisons (verify IDs at platform.claude.com/docs).
TIERS = {
    "opus": "claude-opus-5-5",
    "sonnet": "claude-sonnet-5-5",
    "haiku": "claude-haiku-5-5",
}


def log_usage(label: str, usage: anthropic.types.Usage) -> None:
    """Print a one-line usage summary to stderr. Cache fields are 0 when caching is off."""
    print(
        f"[{label}] input={usage.input_tokens}"
        f" cache_read={usage.cache_read_input_tokens or 0}"
        f" cache_write={usage.cache_creation_input_tokens or 0}"
        f" output={usage.output_tokens}",
        file=sys.stderr,
    )
