"""L10 release data: model lifecycle, the release config, prompt versions, eval runs and a secret scan.

Nothing here calls the API. These are the facts the release gate (starter.py /
solution.py) checks a release against.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import date
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

LAB_DIR = Path(__file__).resolve().parent
PROMPTS_DIR = LAB_DIR / "prompts"
LOCK_FILE = PROMPTS_DIR / "prompts.lock.json"

# --------------------------------------------------------------------------- #
# Model lifecycle on Anthropic-operated platforms, checked 2026-10-26 against
# https://platform.claude.com/docs/en/about-claude/model-deprecations
# Bedrock and Google-managed Vertex set their own dates. Re-check before a release.
# --------------------------------------------------------------------------- #

State = Literal["active", "deprecated", "retired"]


class Lifecycle(BaseModel):
    state: State
    retires: date | None = None  # retirement date (deprecated/retired) or "not sooner than" (active)
    replacement: str | None = None


LIFECYCLE: dict[str, Lifecycle] = {
    "claude-opus-5-5": Lifecycle(state="active", retires=date(2027, 9, 22)),
    "claude-sonnet-5-5": Lifecycle(state="active", retires=date(2027, 9, 28)),
    "claude-haiku-5-5": Lifecycle(state="active", retires=date(2027, 10, 7)),
    "claude-haiku-4-5-20251001": Lifecycle(state="active", retires=date(2026, 10, 15)),
    "claude-sonnet-4-5-20250929": Lifecycle(state="deprecated", retires=date(2026, 11, 30), replacement="claude-sonnet-5-5"),
    "claude-sonnet-4-20250514": Lifecycle(state="retired", retires=date(2026, 6, 15), replacement="claude-sonnet-5-5"),
}

# Older-generation aliases point at a dated snapshot and can move. Current dateless IDs
# (claude-sonnet-5-5) are fixed snapshots themselves. Claude Code's opus/sonnet/haiku move too.
MOVING_ALIASES: dict[str, str | None] = {
    "claude-sonnet-4-5": "claude-sonnet-4-5-20250929",
    "claude-haiku-4-5": "claude-haiku-4-5-20251001",
    "opus": None,
    "sonnet": None,
    "haiku": None,
}


# --------------------------------------------------------------------------- #
# The release config: everything that decides what production does, in one
# reviewed, versioned file. Credentials are NOT in it.
# --------------------------------------------------------------------------- #


class Volume(BaseModel):
    requests_per_week: int
    shared_tokens: int = Field(description="Cached prefix per request")
    unique_tokens: int
    output_tokens: int = Field(description="Measured average, thinking included")
    batch_hit_rate: float = 0.5


class ReleaseConfig(BaseModel):
    release: str
    environment: Literal["dev", "prod"]
    platform: str
    model: str
    prompt: str = Field(description='Prompt reference "name@vN"')
    effort: Literal["low", "medium", "high", "xhigh", "max"]
    max_tokens: int
    batch: bool
    eval_run: str = Field(description="Eval results for exactly this model and prompt, relative to the lab dir")
    baseline_run: str = Field(description="Eval results of what production runs today")
    weekly_budget_usd: float
    volume: Volume


def load_config(path: Path) -> ReleaseConfig:
    return ReleaseConfig.model_validate_json(path.read_text())


# --------------------------------------------------------------------------- #
# Prompts are versioned files: prompts/<name>@v<N>.md. A released version is
# never edited; a change is a new version. The lock records each released hash.
# --------------------------------------------------------------------------- #

PROMPT_REF = re.compile(r"^(?P<name>[a-z0-9-]+)@v(?P<version>\d+)$")


def prompt_path(ref: str, prompts_dir: Path = PROMPTS_DIR) -> Path:
    if not PROMPT_REF.match(ref):
        raise ValueError(f'prompt reference must look like "recap@v2", got {ref!r}')
    return prompts_dir / f"{ref}.md"


def prompt_sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def load_lock(lock_file: Path = LOCK_FILE) -> dict[str, str]:
    return json.loads(lock_file.read_text()) if lock_file.exists() else {}


def lock_prompt(ref: str, prompts_dir: Path = PROMPTS_DIR, lock_file: Path = LOCK_FILE) -> str:
    """Record a prompt version as released. Refuses to change an existing entry."""
    lock = load_lock(lock_file)
    sha = prompt_sha(prompt_path(ref, prompts_dir).read_text())
    if ref in lock and lock[ref] != sha:
        raise ValueError(f"{ref} is already released with a different hash; create a new version instead")
    lock[ref] = sha
    lock_file.write_text(json.dumps(dict(sorted(lock.items())), indent=2) + "\n")
    return sha


# --------------------------------------------------------------------------- #
# Eval runs: recorded results of the recap eval set (20 hand-checked cases).
# --------------------------------------------------------------------------- #


class EvalCase(BaseModel):
    id: str
    passed: bool
    note: str = ""


class EvalRun(BaseModel):
    model: str
    prompt: str
    run_at: date
    cases: list[EvalCase]

    @property
    def pass_rate(self) -> float:
        return sum(c.passed for c in self.cases) / len(self.cases)


def load_eval(path: Path) -> EvalRun:
    return EvalRun.model_validate_json(path.read_text())


# --------------------------------------------------------------------------- #
# Secrets: keys come from the environment, a profile or WIF, never from files.
# --------------------------------------------------------------------------- #

KEY_PATTERN = re.compile(r"sk-ant-[A-Za-z0-9_-]{8,}")
SCANNED_SUFFIXES = {".py", ".json", ".md", ".toml", ".yml", ".yaml", ".txt", ".env", ".cfg", ".ini"}


def scan_for_secrets(root: Path) -> list[str]:
    """Files under root that contain something shaped like an Anthropic key."""
    hits = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and (path.suffix in SCANNED_SUFFIXES or path.name.startswith(".env")):
            if any(part in {".venv", "__pycache__", "out"} for part in path.parts):
                continue
            if KEY_PATTERN.search(path.read_text(errors="ignore")):
                hits.append(str(path.relative_to(root)))
    return hits
