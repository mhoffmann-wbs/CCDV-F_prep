"""L2 cost model: turn token usage into dollars, for each tier, realtime or batch.

Prices are USD per million tokens from the pricing page, checked 2026-10-26:
https://platform.claude.com/docs/en/about-claude/pricing
They change. Re-check them before you trust a report, and keep them in ONE table.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from gridiron.client import TIERS

BATCH_DISCOUNT = 0.5  # stacks with the cache multipliers below


@dataclass(frozen=True)
class Prices:
    input: float
    cache_write_5m: float  # 1.25x input
    cache_write_1h: float  # 2x input
    cache_read: float  # 0.05x input on Opus 5.5 and Sonnet 5.5, 0.1x on Haiku 5.5
    output: float


PRICES: dict[str, Prices] = {
    TIERS["opus"]: Prices(input=4.00, cache_write_5m=5.00, cache_write_1h=8.00, cache_read=0.20, output=20.00),
    TIERS["sonnet"]: Prices(input=2.00, cache_write_5m=2.50, cache_write_1h=4.00, cache_read=0.10, output=10.00),
    TIERS["haiku"]: Prices(input=0.10, cache_write_5m=0.125, cache_write_1h=0.20, cache_read=0.01, output=0.50),
}

# Haiku 5.5 is priced by prompt length: a request whose prompt (input + cache writes +
# cache reads) is over 100K tokens pays these prices for ALL of its tokens.
LONG_PROMPT_THRESHOLD = 100_000
LONG_PROMPT_PRICES: dict[str, Prices] = {
    TIERS["haiku"]: Prices(input=0.50, cache_write_5m=0.625, cache_write_1h=1.00, cache_read=0.05, output=2.50),
}


@dataclass(frozen=True)
class Tokens:
    """One request's usage, split the way it is billed."""

    input: int = 0  # uncached input after the last breakpoint
    cache_write_5m: int = 0
    cache_write_1h: int = 0
    cache_read: int = 0
    output: int = 0  # includes thinking tokens

    @property
    def prompt(self) -> int:
        return self.input + self.cache_write_5m + self.cache_write_1h + self.cache_read

    @classmethod
    def from_usage(cls, usage: Any) -> Tokens:
        """From an API `usage` object. cache_creation splits writes by TTL; older
        responses only have the total, which is billed here as a 5-minute write."""
        split = getattr(usage, "cache_creation", None)
        if split is not None:
            w5, w1 = split.ephemeral_5m_input_tokens, split.ephemeral_1h_input_tokens
        else:
            w5, w1 = usage.cache_creation_input_tokens or 0, 0
        return cls(
            input=usage.input_tokens,
            cache_write_5m=w5,
            cache_write_1h=w1,
            cache_read=usage.cache_read_input_tokens or 0,
            output=usage.output_tokens,
        )

    def __add__(self, other: Tokens) -> Tokens:
        return Tokens(*(a + b for a, b in zip(self._fields(), other._fields())))

    def _fields(self) -> tuple[int, ...]:
        return (self.input, self.cache_write_5m, self.cache_write_1h, self.cache_read, self.output)


def cost(model: str, t: Tokens, *, batch: bool = False) -> float:
    """USD for ONE request's tokens. Call it per request: the long-prompt tier is per request."""
    p = PRICES[model]
    if t.prompt > LONG_PROMPT_THRESHOLD and model in LONG_PROMPT_PRICES:
        p = LONG_PROMPT_PRICES[model]
    usd = (
        t.input * p.input
        + t.cache_write_5m * p.cache_write_5m
        + t.cache_write_1h * p.cache_write_1h
        + t.cache_read * p.cache_read
        + t.output * p.output
    ) / 1_000_000
    return usd * (BATCH_DISCOUNT if batch else 1.0)


def project(
    model: str,
    *,
    requests: int,
    shared: int,
    unique: int,
    output: int,
    batch: bool,
    cache: str,
    hit_rate: float = 1.0,
) -> float:
    """Projected USD for a job of `requests` calls that share `shared` prefix tokens.

    cache="off": every request pays full input for the shared prefix.
    cache="5m" or "1h": the first request writes the prefix; each later one reads it
    with probability `hit_rate` and writes it again on a miss. Batches hit on a
    best-effort basis (the docs report 30-98%), so project them with a hit_rate below 1.
    """
    if cache == "off":
        per = Tokens(input=shared + unique, output=output)
        return requests * cost(model, per, batch=batch)
    write = Tokens(input=unique, output=output, **{f"cache_write_{cache}": shared})
    read = Tokens(input=unique, cache_read=shared, output=output)
    later = requests - 1
    return (
        cost(model, write, batch=batch)
        + later * hit_rate * cost(model, read, batch=batch)
        + later * (1 - hit_rate) * cost(model, write, batch=batch)
    )
