"""Sink registry for ShieldZ Canary Leak Audit.

Registers all locations where application data lands (files, SQLite databases,
logs, journals, Docker outputs) and extracts text/bytes for the Canary scanner.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from shieldz.leak_audit.scanner import LeakFinding, LeakScanner


@dataclass
class SinkInfo:
    """Metadata for a registered data sink."""

    name: str
    path: Path | None = None
    extractor: Callable[[], str | bytes] | None = None
    bytes_scanned: int = 0


class SinkRegistry:
    """Central registry of all sinks where system data lands (Invariant I6)."""

    def __init__(self, runtime_dir: Path | str = "artifacts/runtime") -> None:
        self.runtime_dir = Path(runtime_dir)
        self._sinks: dict[str, SinkInfo] = {}

    def register_file(self, name: str, path: Path | str) -> None:
        """Register a specific file sink."""
        self._sinks[name] = SinkInfo(name=name, path=Path(path))

    def register_custom(self, name: str, extractor: Callable[[], str | bytes]) -> None:
        """Register a custom in-memory extractor (e.g. captured HTTP responses)."""
        self._sinks[name] = SinkInfo(name=name, extractor=extractor)

    def register_default_sinks(self) -> None:
        """Registers the canonical ShieldZ sinks defined in ARCHITECTURE.md §5."""
        self.register_file("app_log", self.runtime_dir / "logs" / "app.jsonl")
        self.register_file("audit_chain", self.runtime_dir / "audit" / "chain.jsonl")
        self.register_file("prompt_journal", self.runtime_dir / "journal" / "prompts.jsonl")
        self.register_file("outbox_sqlite", self.runtime_dir / "outbox.sqlite")
        self.register_file("history_sqlite", self.runtime_dir / "history.sqlite")

    def _extract_sqlite_text(self, db_path: Path) -> tuple[str, int]:
        """Extracts all text column values across all tables in a SQLite database."""
        if not db_path.exists() or db_path.stat().st_size == 0:
            return "", 0

        total_bytes = db_path.stat().st_size
        chunks: list[str] = []

        try:
            conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
            cursor = conn.cursor()
            tables = cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            ).fetchall()

            for (table_name,) in tables:
                col_info = cursor.execute(f"PRAGMA table_info({table_name})").fetchall()
                # col_info: (cid, name, type, notnull, dflt_value, pk)
                text_cols = [c[1] for c in col_info if c[2].upper() in ("TEXT", "VARCHAR", "CHAR")]
                if not text_cols:
                    text_cols = [c[1] for c in col_info]  # check all columns if un-typed

                if text_cols:
                    cols_sql = ", ".join(f'COALESCE(CAST("{c}" AS TEXT), "")' for c in text_cols)
                    rows = cursor.execute(f"SELECT {cols_sql} FROM {table_name}").fetchall()
                    for r in rows:
                        chunks.append(" ".join(r))
            conn.close()
        except Exception:
            # Fallback: scan raw file content if SQLite connection fails
            try:
                raw = db_path.read_text(encoding="utf-8", errors="replace")
                return raw, len(raw.encode("utf-8"))
            except Exception:
                return "", 0

        extracted_text = "\n".join(chunks)
        return extracted_text, total_bytes

    def scan_all(self, scanner: LeakScanner) -> tuple[list[LeakFinding], dict[str, int]]:
        """Scans all registered sinks plus catch-all walk of the runtime directory.

        Returns:
            Tuple of (all_findings, bytes_scanned_per_sink)
        """
        all_findings: list[LeakFinding] = []
        bytes_scanned: dict[str, int] = {}
        scanned_paths: set[Path] = set()

        # 1. Scan registered named sinks
        for name, sink in self._sinks.items():
            if sink.extractor:
                try:
                    data = sink.extractor()
                    if isinstance(data, bytes):
                        text = data.decode("utf-8", errors="replace")
                    else:
                        text = data
                    size = len(text.encode("utf-8"))
                    bytes_scanned[name] = size
                    all_findings.extend(scanner.scan_text(text, sink_name=name))
                except Exception:
                    bytes_scanned[name] = 0
            elif sink.path:
                scanned_paths.add(sink.path.resolve())
                if sink.path.suffix == ".sqlite":
                    text, size = self._extract_sqlite_text(sink.path)
                    bytes_scanned[name] = size
                    if text:
                        all_findings.extend(scanner.scan_text(text, sink_name=name))
                elif sink.path.is_file():
                    try:
                        size = sink.path.stat().st_size
                        bytes_scanned[name] = size
                        all_findings.extend(scanner.scan_file(sink.path, sink_name=name))
                    except Exception:
                        bytes_scanned[name] = 0
                else:
                    bytes_scanned[name] = 0

        # 2. Catch-all walk of runtime directory (Invariant I6)
        if self.runtime_dir.exists():
            for p in self.runtime_dir.rglob("*"):
                if p.is_file() and not p.name.startswith(".") and p.resolve() not in scanned_paths:
                    catch_all_name = f"catch_all:{p.relative_to(self.runtime_dir)}"
                    try:
                        size = p.stat().st_size
                        bytes_scanned[catch_all_name] = size
                        if p.suffix == ".sqlite":
                            text, _ = self._extract_sqlite_text(p)
                            if text:
                                all_findings.extend(
                                    scanner.scan_text(text, sink_name=catch_all_name)
                                )
                        else:
                            all_findings.extend(scanner.scan_file(p, sink_name=catch_all_name))
                    except Exception:
                        bytes_scanned[catch_all_name] = 0

        return all_findings, bytes_scanned
