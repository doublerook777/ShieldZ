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
from typing import Protocol

import numpy as np

from shieldz.privacy.tokenize import Tokenizer

DEMO_SEED = Path(__file__).with_name("demo_seed.csv")


def bucket_prior_inbound(counts):
    """0 -> 0, 1-3 -> 1, 4+ -> 2. Works on ints and numpy arrays; the one definition."""
    counts = np.asarray(counts)
    return (counts >= 1).astype(np.int64) + (counts >= 4).astype(np.int64)


class History(Protocol):
    """What `engineer()` and the service need from a store."""

    def count(self, token: str) -> int: ...

    def bucket(self, token: str) -> int: ...

    def record(self, token: str) -> None: ...


class HistoryStore:
    """In-memory store: training, tests, single-process use."""

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


class SqliteHistoryStore:
    """Same interface, shared by every api worker process through one SQLite file (WAL).

    Counts stay consistent across workers: `record` is a single atomic upsert, and seeding runs
    once per seed name (guarded by a transaction), so concurrent starts cannot double-seed.
    """

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        db = self._conn()
        db.execute(
            "CREATE TABLE IF NOT EXISTS history (token TEXT PRIMARY KEY, n INTEGER NOT NULL)"
        )
        db.execute("CREATE TABLE IF NOT EXISTS seeded (name TEXT PRIMARY KEY)")

    def _conn(self) -> sqlite3.Connection:
        conn = getattr(self._local, "conn", None)
        if conn is None:
            conn = sqlite3.connect(self.path, timeout=5.0, isolation_level=None)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=5000")
            conn.execute("PRAGMA synchronous=NORMAL")
            self._local.conn = conn
        return conn

    def __len__(self) -> int:
        return self._conn().execute("SELECT COUNT(*) FROM history").fetchone()[0]

    def count(self, token: str) -> int:
        row = self._conn().execute("SELECT n FROM history WHERE token = ?", (token,)).fetchone()
        return 0 if row is None else row[0]

    def bucket(self, token: str) -> int:
        return int(bucket_prior_inbound(self.count(token)))

    _UPSERT = (
        "INSERT INTO history (token, n) VALUES (?, ?) ON CONFLICT(token) DO UPDATE SET n = n + ?"
    )

    def record(self, token: str) -> None:
        self._conn().execute(self._UPSERT, (token, 1, 1))

    def seed_counts(self, items: Iterable[tuple[str, int]]) -> None:
        db = self._conn()
        db.execute("BEGIN IMMEDIATE")
        try:
            db.executemany(self._UPSERT, ((t, int(n), int(n)) for t, n in items))
            db.execute("COMMIT")
        except BaseException:
            db.execute("ROLLBACK")
            raise

    def seed_from_csv(self, tokenizer: Tokenizer, path: Path = DEMO_SEED) -> None:
        """Idempotent: the first process to get here seeds, the others see the marker and skip."""
        db = self._conn()
        db.execute("BEGIN IMMEDIATE")
        try:
            if db.execute("SELECT 1 FROM seeded WHERE name = ?", (path.name,)).fetchone():
                db.execute("COMMIT")
                return
            with open(path, newline="") as f:
                rows = [
                    (tokenizer.token(r["payee_account"]), int(r["prior_inbound"]))
                    for r in csv.DictReader(f)
                ]
            db.executemany(self._UPSERT, ((t, n, n) for t, n in rows))
            db.execute("INSERT INTO seeded (name) VALUES (?)", (path.name,))
            db.execute("COMMIT")
        except BaseException:
            db.execute("ROLLBACK")
            raise
