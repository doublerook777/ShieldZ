"""Tamper-evident audit trail with Ed25519 checkpoint signing."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from shieldz.audit.chain import AuditChain, load_chain
from shieldz.audit.signing import CheckpointSigner, generate_keypair, verify_signature

if TYPE_CHECKING:
    from shieldz.audit.verify import verify_audit_trail

__all__ = [
    "AuditChain",
    "CheckpointSigner",
    "generate_keypair",
    "load_chain",
    "verify_audit_trail",
    "verify_signature",
]


def __getattr__(name: str) -> Any:
    if name == "verify_audit_trail":
        from shieldz.audit.verify import verify_audit_trail

        return verify_audit_trail
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
