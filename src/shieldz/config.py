"""Paths and environment settings. Functions, not constants, so tests can override via env vars."""

from __future__ import annotations

import os
from pathlib import Path

# src/shieldz/config.py -> repo root (or /app inside the container)
ROOT = Path(__file__).resolve().parents[2]


def artifacts_dir() -> Path:
    """Gitignored runtime state: model/, keys/, runtime/."""
    return Path(os.environ.get("SHIELDZ_ARTIFACTS", ROOT / "artifacts"))


def keys_dir() -> Path:
    return artifacts_dir() / "keys"


def runtime_dir() -> Path:
    """Everything the running system writes. The Leak Audit walks all of it (invariant I6)."""
    return artifacts_dir() / "runtime"


def model_dir() -> Path:
    return artifacts_dir() / "model"


def thresholds_file() -> Path:
    return model_dir() / "thresholds.json"


def pepper_file() -> Path:
    return keys_dir() / "pepper"
