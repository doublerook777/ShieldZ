"""Prompt and output audit journal (registered Leak Audit sink).

Every prompt sent to the LLM (or fallback) and its generated explanation text
is logged here for accountability, quality monitoring, and canary leakage audits.
"""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

from shieldz.clock import now_utc
from shieldz.config import runtime_dir


class PromptJournal:
    """Thread-safe append-only journal for LLM prompts and explanations."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path if path is not None else runtime_dir() / "journal" / "prompts.jsonl"
        self._lock = threading.Lock()
        self._file = None

    def record(
        self,
        decision_id: str,
        prompt: str,
        text: str,
        source: str,
        language: str,
        guard_passed: bool = True,
    ) -> dict[str, Any]:
        """Append an entry to the prompt journal."""
        entry: dict[str, Any] = {
            "decision_id": decision_id,
            "prompt": prompt,
            "text": text,
            "source": source,
            "language": language,
            "guard_passed": guard_passed,
            "ts": now_utc(),
        }
        line = json.dumps(entry, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"

        with self._lock:
            f = self._open()
            f.write(line)
            f.flush()

        return entry

    def close(self) -> None:
        """Close the underlying file handle."""
        with self._lock:
            if self._file is not None:
                self._file.flush()
                self._file.close()
                self._file = None

    def _open(self):
        if self._file is None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self._file = open(self.path, "a", encoding="utf-8")  # noqa: SIM115
        return self._file


def load_journal(path: Path) -> list[dict[str, Any]]:
    """Load all journal records from the given path."""
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            records.append(json.loads(line))
    return records
