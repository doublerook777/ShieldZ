"""Recipient-novelty store, keyed by HMAC tokens (never raw account ids).

`payee_prior_inbound` is the number of earlier payments the payee received. Training counts it
chronologically over PaySim; serving reads it from here. The count is bucketed (0 / 1-3 / 4+) so
both sides see the same scale. The store is seeded at startup so a fresh service does not treat
every payee as new (cold start, ADR D16):
  - `seed_counts`: e.g. PaySim inbound counts, already tokenized
  - `seed_from_csv`: `features/demo_seed.csv`, fake demo payees with a normal history
"""

from __future__ import annotations

import csv
import sqlite3
import threading
from collections.abc import Iterable
from pathlib import Path

import numpy as np

from shieldz.privacy.tokenize import Tokenizer

DEMO_SEED = Path(__file__).with_name("demo_seed.csv")


def bucket_prior_inbound(counts):
    """0 -> 0, 1-3 -> 1, 4+ -> 2. Works on ints and numpy arrays; the one definition."""
    counts = np.asarray(counts)
    return (counts >= 1).astype(np.int64) + (counts >= 4).astype(np.int64)


class HistoryStore:
    def __init__(self) -> None:
        self._counts: dict[str, int] = {}
        self._lock = threading.Lock()

    def __len__(self) -> int:
        return len(self._counts)

    def count(self, token: str) -> int:
        return self._counts.get(token, 0)

    def bucket(self, token: str) -> int:
        return int(bucket_prior_inbound(self.count(token)))

    def record(self, token: str) -> None:
        """Call after a payment has been scored, so the next one sees it."""
        with self._lock:
            self._counts[token] = self._counts.get(token, 0) + 1

    def seed_counts(self, items: Iterable[tuple[str, int]]) -> None:
        with self._lock:
            for token, n in items:
                self._counts[token] = self._counts.get(token, 0) + int(n)

    def seed_from_csv(self, tokenizer: Tokenizer, path: Path = DEMO_SEED) -> None:
        with open(path, newline="") as f:
            rows = csv.DictReader(f)
            self.seed_counts(
                (tokenizer.token(r["payee_account"]), int(r["prior_inbound"])) for r in rows
            )

    def save(self, path: Path) -> None:
        """Optional SQLite snapshot (tokens and counts only). Registered as a Leak Audit sink."""
        with self._lock, sqlite3.connect(path) as db:
            db.execute("CREATE TABLE IF NOT EXISTS history (token TEXT PRIMARY KEY, n INTEGER)")
            db.executemany("INSERT OR REPLACE INTO history VALUES (?, ?)", self._counts.items())

    def load(self, path: Path) -> None:
        with sqlite3.connect(path) as db:
            self.seed_counts(db.execute("SELECT token, n FROM history"))
