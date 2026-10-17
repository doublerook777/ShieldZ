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
        """Atomically move the oldest pending job to `running` and return it."""
        conn = self._conn()
        conn.execute("BEGIN IMMEDIATE")
        try:
            row = conn.execute(
                "SELECT id, decision_id, decision, risk_level, reason_codes, levels, language"
                " FROM explain_jobs WHERE status = ? ORDER BY id LIMIT 1",
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

    def mark(self, decision_id: str, status: str) -> None:
        self._conn().execute(
            "UPDATE explain_jobs SET status = ? WHERE decision_id = ?", (status, decision_id)
        )

    def put_explanation(self, explanation: Explanation) -> None:
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
