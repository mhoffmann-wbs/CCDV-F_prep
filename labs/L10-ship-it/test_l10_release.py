"""Offline tests for L10: lifecycle, prompt locking, platform fit, the decision record and the gate."""

import importlib.util
import json
import shutil
import sys
from datetime import date
from pathlib import Path

import pytest
from l10_platforms import FEATURES, PLATFORMS, Requirements, adr_markdown, gaps, load_requirements, platform_model_id
from l10_release import LAB_DIR, LIFECYCLE, MOVING_ALIASES, load_config, load_eval, lock_prompt, scan_for_secrets

_spec = importlib.util.spec_from_file_location("l10_solution", Path(__file__).with_name("solution.py"))
solution = importlib.util.module_from_spec(_spec)
sys.modules["l10_solution"] = solution  # dataclasses resolve annotations through sys.modules
_spec.loader.exec_module(solution)

TODAY = date(2026, 10, 26)
REQ = load_requirements(LAB_DIR / "requirements.json")


@pytest.fixture
def lab(tmp_path):
    """A copy of the lab's data files, so tests can edit prompts and the lock freely."""
    for name in ("prompts", "evals"):
        shutil.copytree(LAB_DIR / name, tmp_path / name)
    for name in ("requirements.json", "release.json", "release-solution.json"):
        shutil.copy(LAB_DIR / name, tmp_path / name)
    (tmp_path / ".gitignore").write_text(".env\nout/\n")
    return tmp_path


def ctx(lab, config="release-solution.json", **changes):
    cfg = load_config(lab / config).model_copy(update=changes)
    return solution.Context(
        config=cfg,
        today=TODAY,
        lab_dir=lab,
        prompts_dir=lab / "prompts",
        lock_file=lab / "prompts" / "prompts.lock.json",
        requirements=lab / "requirements.json",
        gitignore=lab / ".gitignore",
    )


def statuses(c):
    return {name: status for name, status, _ in solution.run_gate(c)}


# --- data files ---------------------------------------------------------------


def test_lifecycle_and_aliases_are_consistent():
    for alias, target in MOVING_ALIASES.items():
        assert target is None or target in LIFECYCLE, alias
    for model, info in LIFECYCLE.items():
        assert info.state == "active" or info.replacement in LIFECYCLE, model


def test_eval_runs_tell_the_migration_story():
    base = load_eval(LAB_DIR / "evals/baseline.json")
    v1 = load_eval(LAB_DIR / "evals/sonnet-5-5_recap-v1.json")
    v2 = load_eval(LAB_DIR / "evals/sonnet-5-5_recap-v2.json")
    assert [c.id for c in base.cases] == [c.id for c in v1.cases] == [c.id for c in v2.cases]
    assert v1.pass_rate < base.pass_rate < v2.pass_rate


def test_shipped_lock_matches_v1_and_v2_is_not_released_yet():
    lock = json.loads((LAB_DIR / "prompts/prompts.lock.json").read_text())
    assert set(lock) == {"recap@v1"}


# --- platforms ----------------------------------------------------------------


def test_only_claude_platform_on_aws_meets_the_league_requirements():
    assert {p: gaps(p, REQ) == [] for p in PLATFORMS} == {
        "claude-api": False,  # billed by Anthropic
        "claude-platform-aws": True,
        "bedrock": False,  # no Message Batches API
        "vertex": False,  # GCP billing, no batches
    }
    assert gaps("bedrock", REQ) == ["no message_batches"]


def test_unknown_feature_is_an_error_not_a_silent_pass():
    req = REQ.model_copy(update={"features": ["teleportation"]})
    with pytest.raises(ValueError, match="unknown feature"):
        gaps("claude-api", req)


def test_feature_table_covers_every_platform():
    for feature, row in FEATURES.items():
        assert set(row) == set(PLATFORMS), feature


def test_bedrock_ids_carry_a_prefix():
    assert platform_model_id("bedrock", "claude-sonnet-5-5") == "anthropic.claude-sonnet-5-5"
    assert platform_model_id("claude-platform-aws", "claude-sonnet-5-5") == "claude-sonnet-5-5"


def test_adr_has_the_standard_sections_and_every_option():
    text = adr_markdown(REQ, "claude-platform-aws", "Because.", ["One consequence."])
    for heading in ("## Context", "## Options", "## Decision", "## Consequences"):
        assert heading in text
    assert all(p["name"] in text for p in PLATFORMS.values())
    assert "**Claude Platform on AWS.** Because." in text
    assert isinstance(REQ, Requirements)


# --- prompt versions ----------------------------------------------------------


def test_lock_records_a_version_and_refuses_to_rewrite_it(lab):
    prompts, lock = lab / "prompts", lab / "prompts" / "prompts.lock.json"
    lock_prompt("recap@v2", prompts, lock)
    assert "recap@v2" in json.loads(lock.read_text())
    (prompts / "recap@v2.md").write_text("changed")
    with pytest.raises(ValueError, match="new version"):
        lock_prompt("recap@v2", prompts, lock)


# --- the gate -----------------------------------------------------------------


def test_todays_prod_config_is_blocked_on_five_checks(lab):
    assert statuses(ctx(lab, "release.json")) == {
        "Model pinned": "FAIL",
        "Model lifecycle": "FAIL",
        "Prompt version": "pass",
        "Eval gate": "FAIL",
        "Platform fit": "FAIL",
        "Budget": "FAIL",
        "Secrets": "pass",
    }


def test_fixed_release_passes_once_v2_is_locked(lab):
    assert statuses(ctx(lab))["Prompt version"] == "FAIL"
    lock_prompt("recap@v2", lab / "prompts", lab / "prompts" / "prompts.lock.json")
    assert set(statuses(ctx(lab)).values()) == {"pass"}


def test_editing_a_released_prompt_in_place_is_caught(lab):
    path = lab / "prompts" / "recap@v1.md"
    path.write_text(path.read_text() + "\nOne more rule.\n")
    status, detail = solution.check_prompt_locked(ctx(lab))
    assert status == "FAIL" and "recap@v1" in detail and "new version" in detail


def test_eval_must_match_what_ships_and_have_no_regressions(lab):
    status, detail = solution.check_eval(ctx(lab, prompt="recap@v1"))
    assert status == "FAIL" and "the eval ran" in detail
    status, detail = solution.check_eval(ctx(lab, prompt="recap@v1", eval_run="evals/sonnet-5-5_recap-v1.json"))
    assert status == "FAIL" and "2025-w01-nsh" in detail and "2025-w03-por" in detail


def test_lifecycle_states(lab):
    assert solution.check_lifecycle(ctx(lab, model="claude-sonnet-4-20250514"))[0] == "FAIL"  # retired
    assert solution.check_lifecycle(ctx(lab, model="claude-sonnet-4-5-20250929"))[0] == "FAIL"  # deprecated
    assert solution.check_lifecycle(ctx(lab, model="claude-haiku-4-5-20251001"))[0] == "warn"  # may retire any time
    assert solution.check_lifecycle(ctx(lab))[0] == "pass"


def test_batch_off_for_non_interactive_work_fails(lab):
    status, detail = solution.check_platform(ctx(lab, batch=False))
    assert status == "FAIL" and "batch" in detail


def test_budget_includes_the_us_inference_surcharge(lab):
    c = ctx(lab)
    base = solution.weekly_cost(c.config)
    _, detail = solution.check_budget(c)
    assert f"${base * 1.1:.4f}" in detail
    assert solution.check_budget(ctx(lab, weekly_budget_usd=base))[0] == "FAIL"


def test_secret_scan_finds_keys_and_requires_env_ignored(lab):
    fake = "sk-" + "ant-api03-" + "x" * 20  # built at runtime so this file never contains a key
    (lab / "settings.json").write_text(json.dumps({"key": fake}))
    assert scan_for_secrets(lab) == ["settings.json"]
    assert solution.check_secrets(ctx(lab))[0] == "FAIL"
    (lab / "settings.json").unlink()
    (lab / ".gitignore").write_text("out/\n")
    status, detail = solution.check_secrets(ctx(lab))
    assert status == "FAIL" and ".env" in detail


def test_the_real_lab_folder_has_no_keys():
    assert scan_for_secrets(LAB_DIR) == []
