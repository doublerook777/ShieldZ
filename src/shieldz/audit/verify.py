"""Audit chain and checkpoint verification CLI.

Usage:
    python -m shieldz.audit.verify [chain_file] [--checkpoints CHECKPOINTS] [--pubkey PUBKEY]

Verifies:
    1. Every entry's SHA-256 hash matches its canonical JSON content.
    2. The hash chain is continuous (genesis prev_hash is 64 zeros, each next links to previous).
    3. Sequence numbers are strictly increasing (0, 1, 2, ...).
    4. Any Ed25519 checkpoint signatures in checkpoints.jsonl are cryptographically valid
       and match the chain head at that sequence number.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from shieldz.audit.chain import compute_entry_hash, load_chain
from shieldz.audit.signing import load_checkpoints, verify_signature
from shieldz.contracts import AuditCheckpoint, AuditEntry

GENESIS_HASH = "0" * 64


def verify_audit_trail(
    chain_path: Path,
    checkpoints_path: Path | None = None,
    pubkey_path: Path | None = None,
) -> tuple[bool, str, int | None]:
    """Verify integrity of an audit chain and its signed checkpoints.

    Returns:
        (is_valid, description_message, failure_seq)
    """
    if not chain_path.exists():
        return False, f"Chain file not found: {chain_path}", None

    entries: list[AuditEntry] = load_chain(chain_path)
    if not entries:
        return True, "Chain file is empty (valid)", None

    prev_hash = GENESIS_HASH
    for i, entry in enumerate(entries):
        # 1. Check strictly increasing sequence
        if entry.seq != i:
            msg = f"Sequence break: entry {i} has seq {entry.seq} (expected {i})"
            return False, msg, entry.seq

        # 2. Check prev_hash link
        if entry.prev_hash != prev_hash:
            msg = f"Broken hash chain at seq {entry.seq}: prev_hash does not match preceding entry"
            return False, msg, entry.seq

        # 3. Check entry SHA-256 hash against canonical content
        entry_dict = entry.model_dump(mode="json")
        expected_hash = compute_entry_hash(entry_dict)
        if entry.hash != expected_hash:
            msg = (
                f"Hash mismatch at seq {entry.seq}: stored {entry.hash} != "
                f"recomputed {expected_hash}"
            )
            return False, msg, entry.seq

        prev_hash = entry.hash

    # 4. Check checkpoints if provided
    verified_cps = 0
    if checkpoints_path is not None and checkpoints_path.exists():
        if pubkey_path is None or not pubkey_path.exists():
            return False, f"Checkpoints file exists but pubkey not found at {pubkey_path}", None

        checkpoints: list[AuditCheckpoint] = load_checkpoints(checkpoints_path)
        for cp in checkpoints:
            if cp.seq >= len(entries):
                msg = (
                    f"Checkpoint references seq {cp.seq}, but chain only has {len(entries)} entries"
                )
                return False, msg, cp.seq

            target_entry = entries[cp.seq]
            if cp.head_hash != target_entry.hash:
                msg = (
                    f"Checkpoint head_hash mismatch at seq {cp.seq}: "
                    f"checkpoint has {cp.head_hash}, entry has {target_entry.hash}"
                )
                return False, msg, cp.seq

            # Verify Ed25519 signature over 32 raw bytes of head_hash
            message = bytes.fromhex(cp.head_hash)
            if not verify_signature(pubkey_path, message, cp.signature):
                msg = f"Invalid Ed25519 signature on checkpoint at seq {cp.seq}"
                return False, msg, cp.seq

            verified_cps += 1

    summary = f"Chain valid: {len(entries)} entries verified OK"
    if verified_cps > 0:
        summary += f" ({verified_cps} checkpoint signatures valid)"
    return True, summary, None


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify audit chain integrity and signatures")
    parser.add_argument(
        "chain_file",
        type=Path,
        nargs="?",
        default=Path("artifacts/runtime/audit_chain.jsonl"),
        help="Path to audit chain JSONL file (default: artifacts/runtime/audit_chain.jsonl)",
    )
    parser.add_argument(
        "--checkpoints",
        type=Path,
        default=Path("artifacts/runtime/checkpoints.jsonl"),
        help="Path to checkpoints JSONL file (default: artifacts/runtime/checkpoints.jsonl)",
    )
    parser.add_argument(
        "--pubkey",
        type=Path,
        default=Path("artifacts/keys/audit_pubkey.pem"),
        help="Path to public key PEM (default: artifacts/keys/audit_pubkey.pem)",
    )

    args = parser.parse_args()

    # If default files don't exist, check alternative locations
    checkpoints = args.checkpoints if args.checkpoints.exists() else None
    pubkey = args.pubkey if args.pubkey.exists() else Path("results/audit_pubkey.pem")
    if not pubkey.exists():
        pubkey = None

    valid, message, failure_seq = verify_audit_trail(
        chain_path=args.chain_file,
        checkpoints_path=checkpoints,
        pubkey_path=pubkey,
    )

    if valid:
        print(f"VERIFY PASS: {message}")
        return 0
    else:
        print(f"VERIFY FAIL (seq {failure_seq}): {message}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
