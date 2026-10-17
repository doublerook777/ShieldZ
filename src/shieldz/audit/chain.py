"""Append-only tamper-evident audit chain.

Each entry in ``audit/chain.jsonl`` is a :class:`~shieldz.contracts.AuditEntry` whose
``hash`` field is the SHA-256 of the canonical JSON of every *other* field (sorted keys,
no spaces, UTF-8).  ``prev_hash`` links it to the previous entry (the genesis entry uses
``"0" * 64``), forming a chain that breaks if any byte is altered.

The API runs as a single process, so we use an **in-process threading lock** — there is no
inter-process contention.  The lock is held only for the hash+write step (~microseconds),
so it never adds meaningful latency to the request path.

Usage::

    chain = AuditChain(Path("artifacts/runtime/audit_chain.jsonl"))
    chain.append(decision_id="...", decision="ALLOW", risk_level="LOW", ...)
    chain.close()
"""

from __future__ import annotations

import hashlib
import json
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from shieldz.contracts import AuditEntry

if TYPE_CHECKING:
    from shieldz.contracts import DecisionKind, Level, Reason

GENESIS_HASH = "0" * 64  # prev_hash of the very first entry


def canonical_json(obj: dict[str, Any]) -> bytes:
    """Deterministic JSON: sorted keys, no spaces, UTF-8."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def now_rfc3339() -> str:
    """Current time as RFC 3339 UTC string, e.g. ``2026-10-17T12:34:56Z``."""
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def compute_entry_hash(entry_dict: dict[str, Any]) -> str:
    """Hash a complete AuditEntry dict (without the ``hash`` key itself).

    The dict must contain every field except ``hash``.  The hash is
    SHA-256 of the canonical JSON of those fields.
    """
    payload = {k: v for k, v in entry_dict.items() if k != "hash"}
    return sha256_hex(canonical_json(payload))


def build_entry_dict(
    seq: int,
    ts: str,
    decision_id: str,
    decision: str,
    risk_level: str,
    reason_codes: list[dict[str, str]],
    model_version: str,
    prev_hash: str,
) -> dict[str, Any]:
    """Build and hash an AuditEntry dict."""
    base: dict[str, Any] = {
        "seq": seq,
        "ts": ts,
        "decision_id": decision_id,
        "decision": decision,
        "risk_level": risk_level,
        "reason_codes": reason_codes,
        "model_version": model_version,
        "prev_hash": prev_hash,
    }
    base["hash"] = compute_entry_hash(base)
    return base


def load_chain(chain_path: Path) -> list[AuditEntry]:
    """Read all entries from chain_path and validate as AuditEntry models."""
    if not chain_path.exists():
        return []
    entries: list[AuditEntry] = []
    with open(chain_path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            entries.append(AuditEntry(**data))
    return entries


class AuditChain:
    """Thread-safe append-only audit chain writer.

    One instance is shared across all request handlers in the process.
    The background signing thread in ``signing.py`` reads :attr:`head_hash`
    and :attr:`seq` under the same lock to take consistent checkpoints.

    Parameters
    ----------
    chain_path:
        Path to ``audit/chain.jsonl``.  Created (with parent dirs) if missing.
    """

    def __init__(self, chain_path: Path) -> None:
        self._path = chain_path
        self._lock = threading.Lock()
        self._seq: int = 0
        self._prev_hash: str = GENESIS_HASH
        self._file = None

        if chain_path.exists():
            self._resume()

    @property
    def seq(self) -> int:
        """Number of entries written so far (0 before the first append)."""
        with self._lock:
            return self._seq

    @property
    def head_hash(self) -> str:
        """SHA-256 hex hash of the most recent entry (GENESIS_HASH if empty)."""
        with self._lock:
            return self._prev_hash

    def append(
        self,
        decision_id: str,
        decision: DecisionKind | str,
        risk_level: Level | str,
        reason_codes: list[dict[str, str] | Reason],
        model_version: str,
    ) -> AuditEntry:
        """Append one entry to the chain and return the validated AuditEntry."""
        dec_val = decision.value if hasattr(decision, "value") else str(decision)
        risk_val = risk_level.value if hasattr(risk_level, "value") else str(risk_level)
        reasons_val: list[dict[str, str]] = []
        for r in reason_codes:
            if hasattr(r, "model_dump"):
                d = r.model_dump(mode="json")
                reasons_val.append({"code": str(d["code"]), "level": str(d["level"])})
            elif isinstance(r, dict):
                reasons_val.append({"code": str(r["code"]), "level": str(r["level"])})
            else:
                reasons_val.append({"code": str(r[0]), "level": str(r[1])})

        ts = now_rfc3339()
        with self._lock:
            entry_dict = build_entry_dict(
                seq=self._seq,
                ts=ts,
                decision_id=decision_id,
                decision=dec_val,
                risk_level=risk_val,
                reason_codes=reasons_val,
                model_version=model_version,
                prev_hash=self._prev_hash,
            )
            line = json.dumps(entry_dict, sort_keys=True, separators=(",", ":")) + "\n"
            f = self._open()
            f.write(line)
            f.flush()
            self._prev_hash = entry_dict["hash"]
            self._seq += 1

        return AuditEntry(**entry_dict)

    def close(self) -> None:
        """Flush and close the underlying file handle."""
        with self._lock:
            if self._file is not None:
                self._file.flush()
                self._file.close()
                self._file = None

    def _open(self):
        """Return (and lazily create) the open file handle. Called under self._lock."""
        if self._file is None:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._file = open(self._path, "a", encoding="utf-8")  # noqa: SIM115
        return self._file

    def _resume(self) -> None:
        """Read the last entry in chain.jsonl to resume seq and prev_hash."""
        last_line: str | None = None
        try:
            with open(self._path, encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if line:
                        last_line = line
        except OSError:
            return

        if last_line is None:
            return

        try:
            last = json.loads(last_line)
            self._seq = int(last["seq"]) + 1
            self._prev_hash = str(last["hash"])
        except (json.JSONDecodeError, KeyError, ValueError):
            pass
