import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest
from l2_costs import PRICES, Tokens, cost, project

from gridiron.client import TIERS

OPUS, SONNET, HAIKU = TIERS["opus"], TIERS["sonnet"], TIERS["haiku"]

_spec = importlib.util.spec_from_file_location("l2_solution", Path(__file__).with_name("solution.py"))
solution = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(solution)


def test_cache_multipliers_match_the_pricing_rules():
    for model, p in PRICES.items():
        assert p.cache_write_5m == pytest.approx(1.25 * p.input), model
        assert p.cache_write_1h == pytest.approx(2 * p.input), model
    assert PRICES[OPUS].cache_read == pytest.approx(0.05 * PRICES[OPUS].input)
    assert PRICES[SONNET].cache_read == pytest.approx(0.05 * PRICES[SONNET].input)
    assert PRICES[HAIKU].cache_read == pytest.approx(0.1 * PRICES[HAIKU].input)


def test_cost_per_request():
    t = Tokens(input=1_000_000, output=100_000)
    assert cost(OPUS, t) == pytest.approx(4.0 + 2.0)
    assert cost(OPUS, t, batch=True) == pytest.approx(3.0)  # 50% off everything
    assert cost(SONNET, Tokens(cache_read=1_000_000)) == pytest.approx(0.10)


def test_haiku_long_prompt_tier_applies_to_the_whole_request():
    short = Tokens(input=100_000, output=1_000)
    long = Tokens(input=60_000, cache_read=40_001, output=1_000)  # cache reads count toward the prompt
    assert cost(HAIKU, short) == pytest.approx((100_000 * 0.10 + 1_000 * 0.50) / 1e6)
    assert cost(HAIKU, long) == pytest.approx((60_000 * 0.50 + 40_001 * 0.05 + 1_000 * 2.50) / 1e6)


def test_tokens_from_usage_splits_writes_by_ttl_and_adds_up():
    usage = SimpleNamespace(
        input_tokens=300,
        output_tokens=500,
        cache_read_input_tokens=0,
        cache_creation_input_tokens=1500,
        cache_creation=SimpleNamespace(ephemeral_5m_input_tokens=0, ephemeral_1h_input_tokens=1500),
    )
    t = Tokens.from_usage(usage)
    assert t == Tokens(input=300, cache_write_1h=1500, output=500)
    assert (t + t).cache_write_1h == 3000 and t.prompt == 1800


def test_caching_pays_off_and_batching_halves_it():
    job = {"requests": 12, "shared": 1500, "unique": 300, "output": 800}
    off = project(OPUS, **job, batch=False, cache="off")
    cached = project(OPUS, **job, batch=False, cache="5m")
    assert cached < off
    assert project(OPUS, **job, batch=True, cache="5m") == pytest.approx(cached / 2)
    # Fewer hits cost more; zero hits with a cache costs more than no cache at all.
    assert project(OPUS, **job, batch=True, cache="1h", hit_rate=0.5) > project(OPUS, **job, batch=True, cache="1h")
    assert project(OPUS, **job, batch=False, cache="5m", hit_rate=0) > off


def item(cid, result):
    return SimpleNamespace(custom_id=cid, result=result)


def ok(text, read):
    usage = SimpleNamespace(
        input_tokens=300,
        output_tokens=400,
        cache_read_input_tokens=read,
        cache_creation_input_tokens=0 if read else 1500,
        cache_creation=SimpleNamespace(ephemeral_5m_input_tokens=0, ephemeral_1h_input_tokens=0 if read else 1500),
    )
    message = SimpleNamespace(content=[SimpleNamespace(type="text", text=text)], stop_reason="end_turn", usage=usage)
    return SimpleNamespace(type="succeeded", message=message)


def errored(kind):
    return SimpleNamespace(type="errored", error=SimpleNamespace(error=SimpleNamespace(type=kind)))


def test_collect_keys_by_custom_id_and_sorts_failures(tmp_path):
    results = [  # out of order, as the API may return them
        item("nsh-w3", ok("Mbeki steady again.", read=1500)),
        item("bal-w1", errored("invalid_request_error")),
        item("por-w3", ok("Holloway and Kincaid shine.", read=0)),
        item("sac-w2", errored("overloaded_error")),
        item("sac-w1", SimpleNamespace(type="expired")),
    ]
    r = solution.collect(results, HAIKU, tmp_path)
    assert r["saved"] == ["nsh-w3", "por-w3"]
    assert (tmp_path / "por-w3.md").read_text() == "Holloway and Kincaid shine.\n"
    assert r["fix"] == ["bal-w1"]  # invalid requests fail the same way again
    assert r["resubmit"] == ["sac-w1", "sac-w2"]
    assert r["issues"] == ["por-w3 names Darius Kincaid"]
    assert r["cache_hits"] == 1
    assert r["tokens"] == Tokens(input=600, cache_write_1h=1500, cache_read=1500, output=800)
    assert r["usd"] == pytest.approx(sum(cost(HAIKU, t, batch=True) for t in (
        Tokens(input=300, cache_read=1500, output=400), Tokens(input=300, cache_write_1h=1500, output=400),
    )))  # fmt: skip
