"""One definition of the RFC 3339 UTC timestamp used by logs, the outbox and the audit chain."""

from __future__ import annotations

from datetime import UTC, datetime


def now_utc() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")
