"""SQLite (WAL) outbox between the decision path and the explainer (invariant I3).

The api inserts one `explain_jobs` row per decision (codes, levels, language: no free text). The
explainer claims `pending` rows and writes the `explanations` table. Both containers run the same
image, so the same UID owns the files. The whole file is a Leak Audit sink.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path

from shieldz.clock import now_utc
from shieldz.contracts import DecisionKind, ExplainJob, Explanation

PENDING, RUNNING, DONE, SKIPPED, FAILED = "pending", "running", "done", "skipped", "failed"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS explain_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    decision_id TEXT NOT NULL UNIQUE,
    decision TEXT NOT NULL,
    risk_level TEXT NOT NULL,
    reason_codes TEXT NOT NULL,
    levels TEXT NOT NULL,
    language TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS explain_jobs_status ON explain_jobs (status, id);
CREATE TABLE IF NOT EXISTS explanations (
    decision_id TEXT PRIMARY KEY,
    text TEXT NOT NULL,
    source TEXT NOT NULL,
    language TEXT NOT NULL,
    ts TEXT NOT NULL
);
-- Granite text by hash of the validated prompt. The prompt is a fixed template plus enum values,
-- so the key and the text carry no personal data. Lives in this file, a registered Leak Audit sink.
CREATE TABLE IF NOT EXISTS llm_cache (
    key TEXT PRIMARY KEY,
    text TEXT NOT NULL,
    ts TEXT NOT NULL
);
"""


class Outbox:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self._conn().executescript(_SCHEMA)

    def _conn(self) -> sqlite3.Connection:
        """One connection per thread (the api runs handlers in a thread pool)."""
        conn = getattr(self._local, "conn", None)
        if conn is None:
            conn = sqlite3.connect(self.path, timeout=10.0, isolation_level=None)
            conn.execute("PRAGMA busy_timeout=10000")
            try:
                conn.execute("PRAGMA journal_mode=WAL")
            except sqlite3.OperationalError:
                pass
            conn.execute("PRAGMA synchronous=NORMAL")
            self._local.conn = conn
        return conn

    def enqueue(self, job: ExplainJob) -> None:
        """ALLOW decisions get a row too (audit trail of the count) but are never explained."""
        status = PENDING if job.decision != DecisionKind.ALLOW else SKIPPED
        self._conn().execute(
            "INSERT INTO explain_jobs (decision_id, decision, risk_level, reason_codes, levels,"
            " language, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                job.decision_id,
                job.decision.value,
                job.risk_level.value,
                json.dumps([r.code.value for r in job.reasons]),
                json.dumps([r.level.value for r in job.reasons]),
                job.language.value,
                status,
                now_utc(),
            ),
        )

    def count(self, status: str | None = None) -> int:
        sql, args = "SELECT COUNT(*) FROM explain_jobs", ()
        if status is not None:
            sql, args = sql + " WHERE status = ?", (status,)
        return self._conn().execute(sql, args).fetchone()[0]

    def claim_next(self) -> ExplainJob | None:
        """Atomically move the NEWEST pending job to `running` and return it.

        Newest first, because Granite writes one explanation every ~16 s: after a burst, a
        first-in-first-out queue would answer the payment in front of the user hours late, while an
        old backlog can wait (or be dropped with `skip_pending`)."""
        conn = self._conn()
        conn.execute("BEGIN IMMEDIATE")
        try:
            row = conn.execute(
                "SELECT id, decision_id, decision, risk_level, reason_codes, levels, language"
                " FROM explain_jobs WHERE status = ? ORDER BY id DESC LIMIT 1",
                (PENDING,),
            ).fetchone()
            if row is None:
                conn.execute("COMMIT")
                return None
            conn.execute("UPDATE explain_jobs SET status = ? WHERE id = ?", (RUNNING, row[0]))
            conn.execute("COMMIT")
        except BaseException:
            conn.execute("ROLLBACK")
            raise
        _, decision_id, decision, risk, codes, levels, language = row
        return ExplainJob(
            decision_id=decision_id,
            decision=decision,
            risk_level=risk,
            reasons=[
                {"code": c, "level": lv}
                for c, lv in zip(json.loads(codes), json.loads(levels), strict=True)
            ],
            language=language,
        )

    def requeue_running(self) -> int:
        """After a worker crash: jobs left `running` go back to `pending`. Single-worker only."""
        cur = self._conn().execute(
            "UPDATE explain_jobs SET status = ? WHERE status = ?", (PENDING, RUNNING)
        )
        return cur.rowcount

    def get_cached(self, key: str) -> str | None:
        row = self._conn().execute("SELECT text FROM llm_cache WHERE key = ?", (key,)).fetchone()
        return row[0] if row else None

    def put_cached(self, key: str, text: str) -> None:
        self._conn().execute(
            "INSERT OR REPLACE INTO llm_cache (key, text, ts) VALUES (?, ?, ?)",
            (key, text, now_utc()),
        )

    def drop_cached(self, key: str) -> None:
        self._conn().execute("DELETE FROM llm_cache WHERE key = ?", (key,))

    def clear_cache(self) -> int:
        return self._conn().execute("DELETE FROM llm_cache").rowcount

    def skip_pending(self) -> int:
        """Drop the backlog (e.g. before a demo): pending jobs become `skipped`. Their decisions
        keep the instant template-free result; no explanation is written for them."""
        cur = self._conn().execute(
            "UPDATE explain_jobs SET status = ? WHERE status = ?", (SKIPPED, PENDING)
        )
        return cur.rowcount

    def mark(self, decision_id: str, status: str) -> None:
        self._conn().execute(
            "UPDATE explain_jobs SET status = ? WHERE decision_id = ?", (status, decision_id)
        )

    def put_explanation(self, explanation: Explanation, done: bool = True) -> None:
        """Store (or replace) the explanation. `done=False` keeps the job `running`, so a worker
        can publish the template text first and replace it with the LLM text later."""
        self._conn().execute(
            "INSERT OR REPLACE INTO explanations (decision_id, text, source, language, ts)"
            " VALUES (?, ?, ?, ?, ?)",
            (
                explanation.decision_id,
                explanation.text,
                explanation.source.value,
                explanation.language.value,
                explanation.ts,
            ),
        )
        if done:
            self.mark(explanation.decision_id, DONE)

    def get_explanation(self, decision_id: str) -> Explanation | None:
        row = (
            self._conn()
            .execute(
                "SELECT decision_id, text, source, language, ts FROM explanations"
                " WHERE decision_id = ?",
                (decision_id,),
            )
            .fetchone()
        )
        if row is None:
            return None
        return Explanation(
            decision_id=row[0], text=row[1], source=row[2], language=row[3], ts=row[4]
        )
