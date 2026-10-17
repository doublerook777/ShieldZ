"""Unit tests for M6 tamper-evident audit trail, Ed25519 signing, and verification."""

from __future__ import annotations

import json
from pathlib import Path

from shieldz.audit._ed25519_rfc8032 import (
    generate_keypair_pem,
    public_key_from_seed,
    sign,
    sign_pem,
    verify,
    verify_pem,
)
from shieldz.audit.chain import AuditChain, load_chain
from shieldz.audit.signing import (
    BACKEND,
    CheckpointSigner,
    generate_keypair,
    load_checkpoints,
    verify_signature,
)
from shieldz.audit.verify import verify_audit_trail
from shieldz.contracts import DecisionKind, Level, ReasonCode


def test_backend_loaded() -> None:
    """Verify an active backend is selected (cryptography or rfc8032)."""
    assert BACKEND in ("cryptography", "rfc8032")


def test_rfc8032_section_7_1_test_vectors() -> None:
    """Validate Ed25519 implementation against all RFC 8032 §7.1 test vectors."""
    # Test 1
    seed1 = bytes.fromhex("9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60")
    pub1 = bytes.fromhex("d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a")
    msg1 = b""
    sig1 = bytes.fromhex(
        "e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e06522490155"
        "5fb8821590a33bacc61e39701cf9b46bd25bf5f0595bbe24655141438e7a100b"
    )
    assert public_key_from_seed(seed1) == pub1
    assert sign(seed1, msg1) == sig1
    assert verify(pub1, msg1, sig1) is True

    # Test 2
    seed2 = bytes.fromhex("4ccd089b28ff96da9db6c346ec114e0f5b8a319f35aba624da8cf6ed4fb8a6fb")
    pub2 = bytes.fromhex("3d4017c3e843895a92b70aa74d1b7ebc9c982ccf2ec4968cc0cd55f12af4660c")
    msg2 = bytes.fromhex("72")
    sig2 = bytes.fromhex(
        "92a009a9f0d4cab8720e820b5f642540a2b27b5416503f8fb3762223ebdb69da"
        "085ac1e43e15996e458f3613d0f11d8c387b2eaeb4302aeeb00d291612bb0c00"
    )
    assert public_key_from_seed(seed2) == pub2
    assert sign(seed2, msg2) == sig2
    assert verify(pub2, msg2, sig2) is True

    # Test 3
    seed3 = bytes.fromhex("c5aa8df43f9f837bedb7442f31dcb7b166d38535076f094b85ce3a2e0b4458f7")
    pub3 = bytes.fromhex("fc51cd8e6218a1a38da47ed00230f0580816ed13ba3303ac5deb911548908025")
    msg3 = bytes.fromhex("af82")
    sig3 = bytes.fromhex(
        "6291d657deec24024827e69c3abe01a30ce548a284743a445e3680d7db5ac3ac"
        "18ff9b538d16f290ae67f760984dc6594a7c15e9716ed28dc027beceea1ec40a"
    )
    assert public_key_from_seed(seed3) == pub3
    assert sign(seed3, msg3) == sig3
    assert verify(pub3, msg3, sig3) is True


def test_pem_roundtrip() -> None:
    priv_pem, pub_pem = generate_keypair_pem()
    msg = b"tamper-evident audit checkpoint"
    sig = sign_pem(priv_pem, msg)
    assert verify_pem(pub_pem, msg, sig) is True
    assert verify_pem(pub_pem, b"other message", sig) is False


def test_chain_append_and_resume(tmp_path: Path) -> None:
    chain_file = tmp_path / "chain.jsonl"
    chain = AuditChain(chain_file)

    assert chain.seq == 0
    assert chain.head_hash == "0" * 64

    entry0 = chain.append(
        decision_id="dec-0",
        decision=DecisionKind.ALLOW,
        risk_level=Level.LOW,
        reason_codes=[],
        model_version="xgb-1.0",
    )
    assert entry0.seq == 0
    assert entry0.prev_hash == "0" * 64
    assert chain.seq == 1
    assert chain.head_hash == entry0.hash

    entry1 = chain.append(
        decision_id="dec-1",
        decision=DecisionKind.BLOCK,
        risk_level=Level.HIGH,
        reason_codes=[{"code": ReasonCode.ACCOUNT_DRAIN, "level": Level.HIGH}],
        model_version="xgb-1.0",
    )
    assert entry1.seq == 1
    assert entry1.prev_hash == entry0.hash
    assert chain.seq == 2
    assert chain.head_hash == entry1.hash

    chain.close()

    # Reopen to test resume
    chain2 = AuditChain(chain_file)
    assert chain2.seq == 2
    assert chain2.head_hash == entry1.hash

    entry2 = chain2.append(
        decision_id="dec-2",
        decision=DecisionKind.REVIEW,
        risk_level=Level.MEDIUM,
        reason_codes=[{"code": ReasonCode.NEW_RECIPIENT, "level": Level.MEDIUM}],
        model_version="xgb-1.0",
    )
    assert entry2.seq == 2
    assert entry2.prev_hash == entry1.hash
    chain2.close()

    loaded = load_chain(chain_file)
    assert len(loaded) == 3
    assert loaded[0].decision_id == "dec-0"
    assert loaded[1].decision_id == "dec-1"
    assert loaded[2].decision_id == "dec-2"


def test_checkpoint_signing_and_verification(tmp_path: Path) -> None:
    chain_file = tmp_path / "chain.jsonl"
    cp_file = tmp_path / "checkpoints.jsonl"
    priv_file = tmp_path / "keys" / "audit_privkey.pem"
    pub_file = tmp_path / "keys" / "audit_pubkey.pem"

    generate_keypair(priv_file, pub_file)
    assert priv_file.exists()
    assert pub_file.exists()

    chain = AuditChain(chain_file)
    signer = CheckpointSigner(chain, cp_file, priv_file, pub_file)

    for i in range(10):
        chain.append(
            decision_id=f"dec-{i}",
            decision=DecisionKind.ALLOW,
            risk_level=Level.LOW,
            reason_codes=[],
            model_version="v1",
        )

    # Force a checkpoint
    cp = signer.checkpoint_now(force=True)
    assert cp is not None
    assert cp.seq == 9
    assert cp.head_hash == chain.head_hash
    assert verify_signature(pub_file, bytes.fromhex(cp.head_hash), cp.signature) is True

    chain.close()

    cps = load_checkpoints(cp_file)
    assert len(cps) == 1
    assert cps[0].seq == 9

    valid, msg, fail_seq = verify_audit_trail(chain_file, cp_file, pub_file)
    assert valid is True
    assert fail_seq is None
    assert "10 entries verified OK" in msg


def test_tamper_detection_modified_content(tmp_path: Path) -> None:
    chain_file = tmp_path / "chain.jsonl"
    chain = AuditChain(chain_file)
    for i in range(5):
        chain.append(
            decision_id=f"dec-{i}",
            decision=DecisionKind.ALLOW,
            risk_level=Level.LOW,
            reason_codes=[],
            model_version="v1",
        )
    chain.close()

    # Tamper with entry at seq 2: change ALLOW to BLOCK without recalculating hash
    lines = chain_file.read_text(encoding="utf-8").splitlines()
    data = json.loads(lines[2])
    data["decision"] = "BLOCK"
    lines[2] = json.dumps(data)
    chain_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

    valid, msg, fail_seq = verify_audit_trail(chain_file)
    assert valid is False
    assert fail_seq == 2
    assert "Hash mismatch at seq 2" in msg


def test_tamper_detection_deleted_line(tmp_path: Path) -> None:
    chain_file = tmp_path / "chain.jsonl"
    chain = AuditChain(chain_file)
    for i in range(5):
        chain.append(
            decision_id=f"dec-{i}",
            decision=DecisionKind.ALLOW,
            risk_level=Level.LOW,
            reason_codes=[],
            model_version="v1",
        )
    chain.close()

    # Delete entry at seq 2
    lines = chain_file.read_text(encoding="utf-8").splitlines()
    del lines[2]
    chain_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

    valid, msg, fail_seq = verify_audit_trail(chain_file)
    assert valid is False
    assert fail_seq == 3
    assert "Sequence break" in msg


def test_tamper_detection_swapped_lines(tmp_path: Path) -> None:
    chain_file = tmp_path / "chain.jsonl"
    chain = AuditChain(chain_file)
    for i in range(5):
        chain.append(
            decision_id=f"dec-{i}",
            decision=DecisionKind.ALLOW,
            risk_level=Level.LOW,
            reason_codes=[],
            model_version="v1",
        )
    chain.close()

    # Swap entries 1 and 2
    lines = chain_file.read_text(encoding="utf-8").splitlines()
    lines[1], lines[2] = lines[2], lines[1]
    chain_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

    valid, msg, fail_seq = verify_audit_trail(chain_file)
    assert valid is False
    assert fail_seq in (1, 2)


def test_tamper_detection_invalid_signature(tmp_path: Path) -> None:
    chain_file = tmp_path / "chain.jsonl"
    cp_file = tmp_path / "checkpoints.jsonl"
    priv_file = tmp_path / "keys" / "audit_privkey.pem"
    pub_file = tmp_path / "keys" / "audit_pubkey.pem"

    generate_keypair(priv_file, pub_file)
    chain = AuditChain(chain_file)
    signer = CheckpointSigner(chain, cp_file, priv_file, pub_file)

    for i in range(3):
        chain.append(
            decision_id=f"dec-{i}",
            decision=DecisionKind.ALLOW,
            risk_level=Level.LOW,
            reason_codes=[],
            model_version="v1",
        )

    signer.checkpoint_now(force=True)
    chain.close()

    # Corrupt the signature in checkpoints.jsonl
    lines = cp_file.read_text(encoding="utf-8").splitlines()
    cp_data = json.loads(lines[0])
    cp_data["signature"] = "0" * 128  # corrupt signature
    lines[0] = json.dumps(cp_data)
    cp_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

    valid, msg, fail_seq = verify_audit_trail(chain_file, cp_file, pub_file)
    assert valid is False
    assert fail_seq == 2
    assert "Invalid Ed25519 signature" in msg
