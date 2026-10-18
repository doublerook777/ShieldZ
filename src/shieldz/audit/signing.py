"""Ed25519 signing of audit chain checkpoints.

A **checkpoint** is a signed snapshot of the chain head: one Ed25519 signature covers
the ``head_hash`` bytes (32 raw bytes decoded from hex) at a given ``seq``. Because the
chain is a hash chain, this one signature transitively covers every entry up to that point.

Signing **never runs in the request path**. A background daemon thread fires every
100 new entries *or* every second (whichever comes first) and appends one
``AuditCheckpoint`` line to ``audit/checkpoints.jsonl``.

Backend selection (tries each in order; some s390x images have no `cryptography` wheel):
    1. ``cryptography`` from Ubuntu apt / pip (preferred; C-accelerated, hardware-aware on z15+)
    2. Pure-Python Ed25519 from RFC 8032 (our own implementation; passes all §7.1 test vectors)

Key management:
    - Private key: ``artifacts/keys/audit_privkey.pem``  — **never committed**
    - Public  key: ``artifacts/keys/audit_pubkey.pem``   — exported to ``results/``
    - Keys are generated once on first run; ``generate_keypair()`` is idempotent.

Usage::

    signer = CheckpointSigner(chain, checkpoints_path, privkey_path, pubkey_path)
    signer.start()    # called at service startup
    signer.stop()     # called at shutdown (waits for the final checkpoint)
"""

from __future__ import annotations

import json
import threading
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from shieldz.contracts import AuditCheckpoint

if TYPE_CHECKING:
    from shieldz.audit.chain import AuditChain

_CHECKPOINT_EVERY_N = 100  # entries
_CHECKPOINT_EVERY_S = 1.0  # seconds


def _now_rfc3339() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# Ed25519 backend loader
# ---------------------------------------------------------------------------


def _load_backend() -> tuple[
    str,
    Callable[[bytes, bytes], bytes],
    Callable[[bytes, bytes, bytes], bool],
    Callable[[], tuple[bytes, bytes]],
]:
    """Return (backend_name, sign_fn, verify_fn, generate_fn)."""
    try:
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric.ed25519 import (
            Ed25519PrivateKey,
            Ed25519PublicKey,
        )

        def _sign_crypto(privkey_pem: bytes, message: bytes) -> bytes:
            key = serialization.load_pem_private_key(privkey_pem, password=None)
            if not isinstance(key, Ed25519PrivateKey):
                raise TypeError("Private key is not Ed25519")
            return key.sign(message)

        def _verify_crypto(pubkey_pem: bytes, message: bytes, signature: bytes) -> bool:
            try:
                key = serialization.load_pem_public_key(pubkey_pem)
                if not isinstance(key, Ed25519PublicKey):
                    return False
                key.verify(signature, message)
                return True
            except Exception:
                return False

        def _generate_crypto() -> tuple[bytes, bytes]:
            priv = Ed25519PrivateKey.generate()
            priv_pem = priv.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.PKCS8,
                serialization.NoEncryption(),
            )
            pub_pem = priv.public_key().public_bytes(
                serialization.Encoding.PEM,
                serialization.PublicFormat.SubjectPublicKeyInfo,
            )
            return priv_pem, pub_pem

        return "cryptography", _sign_crypto, _verify_crypto, _generate_crypto

    except ImportError:
        pass

    # Pure Python RFC 8032 fallback
    from shieldz.audit._ed25519_rfc8032 import (
        generate_keypair_pem,
        sign_pem,
        verify_pem,
    )

    return "rfc8032", sign_pem, verify_pem, generate_keypair_pem


_BACKEND_NAME, _sign_fn, _verify_fn, _generate_fn = _load_backend()
BACKEND = _BACKEND_NAME  # visible for tests / progress.md


# ---------------------------------------------------------------------------
# Key management
# ---------------------------------------------------------------------------


def generate_keypair(privkey_path: Path, pubkey_path: Path) -> None:
    """Generate an Ed25519 key pair and write PEM files.

    Idempotent: does nothing if both files already exist.
    """
    if privkey_path.exists() and pubkey_path.exists():
        return
    privkey_path.parent.mkdir(parents=True, exist_ok=True)
    pubkey_path.parent.mkdir(parents=True, exist_ok=True)
    priv_pem, pub_pem = _generate_fn()
    privkey_path.write_bytes(priv_pem)
    pubkey_path.write_bytes(pub_pem)
    privkey_path.chmod(0o600)


def sign_bytes(privkey_path: Path, message: bytes) -> str:
    """Sign *message* with the private key at *privkey_path*. Returns hex signature."""
    priv_pem = privkey_path.read_bytes()
    sig = _sign_fn(priv_pem, message)
    return sig.hex()


def verify_signature(pubkey: Path | bytes, message: bytes, signature_hex: str) -> bool:
    """Verify *signature_hex* on *message* using the public key PEM."""
    try:
        pub_pem = pubkey.read_bytes() if isinstance(pubkey, Path) else pubkey
        sig_bytes = bytes.fromhex(signature_hex)
        return _verify_fn(pub_pem, message, sig_bytes)
    except Exception:
        return False


def load_checkpoints(checkpoints_path: Path) -> list[AuditCheckpoint]:
    """Read all checkpoints from JSONL file."""
    if not checkpoints_path.exists():
        return []
    cps: list[AuditCheckpoint] = []
    with open(checkpoints_path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            cps.append(AuditCheckpoint(**data))
    return cps


# ---------------------------------------------------------------------------
# Background checkpoint signer
# ---------------------------------------------------------------------------


class CheckpointSigner:
    """Background daemon thread that signs the chain head periodically.

    Fires every :data:`_CHECKPOINT_EVERY_N` new entries or every
    :data:`_CHECKPOINT_EVERY_S` seconds, whichever comes first.
    """

    def __init__(
        self,
        chain: AuditChain,
        checkpoints_path: Path,
        privkey_path: Path,
        pubkey_path: Path,
    ) -> None:
        self._chain = chain
        self._checkpoints_path = checkpoints_path
        self._privkey_path = privkey_path
        self._pubkey_path = pubkey_path

        self._last_signed_seq: int = -1
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._loop, name="audit-signer", daemon=True)

    def start(self) -> None:
        """Generate keys (if needed) and start the background thread."""
        generate_keypair(self._privkey_path, self._pubkey_path)
        self._thread.start()

    def stop(self, timeout: float = 5.0) -> None:
        """Signal the thread to stop and wait for one final checkpoint."""
        self._stop_event.set()
        self._thread.join(timeout=timeout)
        self.checkpoint_now(force=True)

    def checkpoint_now(self, force: bool = False) -> AuditCheckpoint | None:
        """Immediately compute and write a checkpoint if there are new entries."""
        seq = self._chain.seq
        head = self._chain.head_hash

        if seq == 0:
            return None
        if not force and seq - 1 == self._last_signed_seq:
            return None

        try:
            message = bytes.fromhex(head)
            sig_hex = sign_bytes(self._privkey_path, message)
            cp = AuditCheckpoint(
                seq=seq - 1,
                head_hash=head,
                ts=_now_rfc3339(),
                signature=sig_hex,
            )
            line = json.dumps(cp.model_dump(), sort_keys=True, separators=(",", ":")) + "\n"
            self._checkpoints_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._checkpoints_path, "a", encoding="utf-8") as fh:
                fh.write(line)
                fh.flush()
            self._last_signed_seq = seq - 1
            return cp
        except Exception:  # noqa: BLE001
            return None

    def _loop(self) -> None:
        last_time = time.monotonic()
        while not self._stop_event.is_set():
            now = time.monotonic()
            elapsed = now - last_time
            current_seq = self._chain.seq

            n_new = current_seq - (self._last_signed_seq + 1)
            time_due = elapsed >= _CHECKPOINT_EVERY_S
            entries_due = n_new >= _CHECKPOINT_EVERY_N

            if entries_due or time_due:
                self.checkpoint_now()
                last_time = time.monotonic()

            self._stop_event.wait(timeout=0.1)
