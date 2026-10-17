"""Canary Leak Scanner for ShieldZ.

Scans text, binary data, files, and directories for any leaked canary values in exact,
variant (base64, hex, digits-only, stripped, unsalted hash), or partial forms.
"""

from __future__ import annotations

import base64
import hashlib
import re
import urllib.parse
from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from shieldz.leak_audit.canaries import CanaryRecord


class LeakSeverity(StrEnum):
    EXACT = "EXACT"
    VARIANT = "VARIANT"
    PARTIAL = "PARTIAL"


@dataclass(frozen=True)
class LeakFinding:
    """Details of a single leaked canary value detected by the scanner."""

    canary_id: str
    field_name: str
    matched_value: str
    variant_type: str
    severity: LeakSeverity
    sink_name: str
    context: str = ""


class LeakScanner:
    """High-performance multi-variant scanner for Canary PII."""

    def __init__(
        self,
        canaries: Iterable[CanaryRecord],
        allowed_tokens: set[str] | None = None,
    ) -> None:
        self.canaries = list(canaries)
        self.allowed_tokens: set[str] = set(allowed_tokens or ())

        # variant_str -> (canary_id, field_name, variant_type, severity)
        self._exact_and_variants: dict[str, tuple[str, str, str, LeakSeverity]] = {}
        # 7+ digit pattern -> (canary_id, field_name)
        self._partial_digit_runs: dict[str, tuple[str, str]] = {}

        self._build_index()

    def add_allowed_token(self, token: str) -> None:
        """Register an allowed token (e.g. HMAC account token) to exempt from findings."""
        self.allowed_tokens.add(token)

    def _build_index(self) -> None:
        """Precomputes exact patterns, variants, and partial digit substrings."""
        for c in self.canaries:
            # 1. String fields
            text_fields = {
                "payer_name": c.payer_name,
                "payee_name": c.payee_name,
                "payer_phone": c.payer_phone,
                "payer_account": c.payer_account,
                "payee_account": c.payee_account,
                "upi_id": c.upi_id,
                "email": c.email,
                "memo": c.memo,
                "amount": f"{c.amount:.2f}",
            }

            for field, val in text_fields.items():
                if not val or len(val) < 4:
                    continue

                # Exact match
                self._exact_and_variants[val] = (c.canary_id, field, "exact", LeakSeverity.EXACT)

                # Lowercase / Case-folded
                val_lower = val.lower()
                if val_lower != val:
                    self._exact_and_variants[val_lower] = (
                        c.canary_id,
                        field,
                        "case_folded",
                        LeakSeverity.VARIANT,
                    )

                # Whitespace/dash stripped
                stripped = re.sub(r"[\s\-_/]+", "", val)
                if stripped != val and len(stripped) >= 5:
                    self._exact_and_variants[stripped] = (
                        c.canary_id,
                        field,
                        "stripped",
                        LeakSeverity.VARIANT,
                    )

                # Digits-only for phones and accounts
                if field in ("payer_phone", "payer_account", "payee_account"):
                    digits_only = re.sub(r"\D", "", val)
                    if digits_only and digits_only not in (val, stripped) and len(digits_only) >= 7:
                        self._exact_and_variants[digits_only] = (
                            c.canary_id,
                            field,
                            "digits_only",
                            LeakSeverity.VARIANT,
                        )

                # URL-encoded
                url_enc = urllib.parse.quote(val)
                if url_enc != val:
                    self._exact_and_variants[url_enc] = (
                        c.canary_id,
                        field,
                        "url_encoded",
                        LeakSeverity.VARIANT,
                    )

                # Base64 encoded
                b64 = base64.b64encode(val.encode("utf-8")).decode("ascii")
                self._exact_and_variants[b64] = (c.canary_id, field, "base64", LeakSeverity.VARIANT)

                # Hex encoded
                hex_enc = val.encode("utf-8").hex()
                self._exact_and_variants[hex_enc] = (
                    c.canary_id,
                    field,
                    "hex",
                    LeakSeverity.VARIANT,
                )

                # Unsalted cryptographic hashes (MD5, SHA-1, SHA-256)
                raw_bytes = val.encode("utf-8")
                md5_hex = hashlib.md5(raw_bytes).hexdigest()  # noqa: S324
                sha1_hex = hashlib.sha1(raw_bytes).hexdigest()  # noqa: S324
                sha256_hex = hashlib.sha256(raw_bytes).hexdigest()

                self._exact_and_variants[md5_hex] = (
                    c.canary_id,
                    field,
                    "md5",
                    LeakSeverity.VARIANT,
                )
                self._exact_and_variants[sha1_hex] = (
                    c.canary_id,
                    field,
                    "sha1",
                    LeakSeverity.VARIANT,
                )
                self._exact_and_variants[sha256_hex] = (
                    c.canary_id,
                    field,
                    "sha256",
                    LeakSeverity.VARIANT,
                )

                # Partial digit indexing: standalone 7+ digit runs for phones and accounts
                if field in ("payer_phone", "payer_account", "payee_account"):
                    clean_digits = re.sub(r"\D", "", val)
                    if len(clean_digits) >= 7:
                        # Index standalone 7-digit substrings
                        for start in range(len(clean_digits) - 6):
                            sub = clean_digits[start : start + 7]
                            if sub not in self._partial_digit_runs:
                                self._partial_digit_runs[sub] = (c.canary_id, field)

    def scan_text(self, text: str, sink_name: str = "text") -> list[LeakFinding]:
        """Scans a string of text for any canary leaks.

        Args:
            text: Input text content to scan.
            sink_name: Identifier for the source sink (e.g. "logs/app.jsonl").

        Returns:
            List of detected LeakFinding entries.
        """
        findings: list[LeakFinding] = []
        if not text:
            return findings

        # Mask out any registered allowed tokens (e.g. valid HMAC tokens)
        scan_target = text
        for token in self.allowed_tokens:
            if token:
                scan_target = scan_target.replace(token, "[EXEMPTED_TOKEN]")

        # Check exact & full variants
        for pattern, (canary_id, field, vtype, severity) in self._exact_and_variants.items():
            if pattern in self.allowed_tokens:
                continue

            if pattern in scan_target:
                # Find context snippet around the match
                idx = scan_target.find(pattern)
                start = max(0, idx - 20)
                end = min(len(scan_target), idx + len(pattern) + 20)
                context = scan_target[start:end].replace("\n", " ")

                findings.append(
                    LeakFinding(
                        canary_id=canary_id,
                        field_name=field,
                        matched_value=pattern,
                        variant_type=vtype,
                        severity=severity,
                        sink_name=sink_name,
                        context=context,
                    )
                )

        # Check partial standalone digit runs (7 to 12 digits bounded by non-alphanumerics)
        # Bounded so random digits inside hex hashes/UUIDs don't trigger false positives
        standalone_runs = re.findall(r"(?<![0-9a-zA-Z])\d{7,12}(?![0-9a-zA-Z])", scan_target)
        for run in standalone_runs:
            if run in self.allowed_tokens or run in self._exact_and_variants:
                continue  # already checked or exempted

            # Check if this standalone run contains any canary's 7+ digit sequence
            for sub, (canary_id, field) in self._partial_digit_runs.items():
                if sub in run:
                    findings.append(
                        LeakFinding(
                            canary_id=canary_id,
                            field_name=field,
                            matched_value=run,
                            variant_type="partial_digit_run",
                            severity=LeakSeverity.PARTIAL,
                            sink_name=sink_name,
                            context=f"...{run}...",
                        )
                    )
                    break

        return findings

    def scan_file(self, file_path: Path | str, sink_name: str | None = None) -> list[LeakFinding]:
        """Scans a file on disk, handling both text and binary formats gracefully."""
        path = Path(file_path)
        name = sink_name or str(path)
        if not path.is_file():
            return []

        try:
            content = path.read_text(encoding="utf-8", errors="replace")
            return self.scan_text(content, sink_name=name)
        except Exception:
            return []

    def scan_directory(self, dir_path: Path | str) -> list[LeakFinding]:
        """Recursively scans all files in a directory."""
        findings: list[LeakFinding] = []
        root = Path(dir_path)
        if not root.is_dir():
            return findings

        for p in root.rglob("*"):
            if p.is_file():
                findings.extend(self.scan_file(p))
        return findings
