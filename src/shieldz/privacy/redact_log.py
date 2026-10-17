"""JSON logging with a field allowlist (invariant I4).

Only known-safe keys are written; everything else is dropped, not redacted. Free-text messages and
tracebacks are never written, because they can contain whatever an exception happened to print.
Values must be short scalars; anything else is dropped too.
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

from shieldz.clock import now_utc
from shieldz.config import runtime_dir

ALLOWED_FIELDS = frozenset(
    {
        "event",
        "decision_id",
        "decision",
        "risk_level",
        "reason_codes",
        "model_version",
        "engine",
        "server_ms",
        "status",
        "source",
        "language",
        "error_type",
        "count",
        "platform",
    }
)
_MAX_STR = 64
LOGGER_NAME = "shieldz"


def _safe_value(value):
    if isinstance(value, bool) or value is None or isinstance(value, int | float):
        return value
    if isinstance(value, str) and len(value) <= _MAX_STR:
        return value
    if isinstance(value, list | tuple) and len(value) <= 8:
        items = [_safe_value(v) for v in value]
        return None if any(i is None for i in items) else items
    return None  # dropped by the caller


def allowlisted(fields: dict) -> dict:
    out = {}
    for key, value in fields.items():
        if key not in ALLOWED_FIELDS:
            continue
        safe = _safe_value(value)
        if safe is not None or value is None:
            out[key] = safe
    return out


class AllowlistFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        fields = getattr(record, "fields", {})
        return json.dumps({"ts": now_utc(), **allowlisted(fields)}, separators=(",", ":"))


def log_path() -> Path:
    return runtime_dir() / "logs" / "app.jsonl"


def setup_logging(path: Path | None = None, stream=None) -> logging.Logger:
    """File (a Leak Audit sink) plus container stdout, same formatter. Safe to call repeatedly."""
    logger = logging.getLogger(LOGGER_NAME)
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()
    logger.setLevel(logging.INFO)
    logger.propagate = False
    fmt = AllowlistFormatter()
    path = path or log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    for handler in (
        logging.FileHandler(path, encoding="utf-8"),
        logging.StreamHandler(stream or sys.stdout),
    ):
        handler.setFormatter(fmt)
        logger.addHandler(handler)
    return logger


def log_event(event: str, **fields) -> None:
    """The only way application code logs. `exc_info`, messages and unknown keys cannot get in."""
    logging.getLogger(LOGGER_NAME).info("", extra={"fields": {"event": event, **fields}})
