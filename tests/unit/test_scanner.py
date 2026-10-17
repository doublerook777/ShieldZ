import base64
import hashlib

from shieldz.leak_audit.canaries import generate_canaries, generate_decoys
from shieldz.leak_audit.scanner import LeakScanner, LeakSeverity


def test_clean_text_produces_zero_findings():
    canaries = generate_canaries(n=50, seed=42)
    scanner = LeakScanner(canaries)
    clean_log = (
        '{"timestamp": "2026-10-17T16:00:00Z", "decision": "ALLOW"}\n'
        '{"timestamp": "2026-10-17T16:00:01Z", "msg": "Audit written", "seq": 1042}\n'
    )
    findings = scanner.scan_text(clean_log)
    assert len(findings) == 0


def test_exact_matches_detected():
    canaries = generate_canaries(n=10, seed=42)
    target = canaries[3]
    scanner = LeakScanner(canaries)

    text = f"Leaked user: {target.payer_name} with account {target.payer_account}"
    findings = scanner.scan_text(text)

    severities = [f.severity for f in findings]
    assert LeakSeverity.EXACT in severities

    matched_canaries = {f.canary_id for f in findings}
    assert target.canary_id in matched_canaries


def test_variant_matches_detected():
    canaries = generate_canaries(n=10, seed=42)
    target = canaries[5]
    scanner = LeakScanner(canaries)

    # Base64 variant
    b64_name = base64.b64encode(target.payer_name.encode("utf-8")).decode("ascii")
    # Hex variant
    hex_account = target.payer_account.encode("utf-8").hex()
    # SHA-256 hash variant
    hash_memo = hashlib.sha256(target.memo.encode("utf-8")).hexdigest()

    text = f"Base64: {b64_name}, Hex: {hex_account}, Hash: {hash_memo}"
    findings = scanner.scan_text(text)

    types = {f.variant_type for f in findings}
    assert "base64" in types
    assert "hex" in types
    assert "sha256" in types


def test_allowed_hmac_tokens_are_not_flagged():
    import hmac

    canaries = generate_canaries(n=10, seed=42)
    target = canaries[0]

    # Real HMAC token
    hmac_token = hmac.new(b"secret_pepper_123", target.payer_account.encode(), "sha256").hexdigest()
    scanner = LeakScanner(canaries, allowed_tokens={hmac_token})

    text = f"Safe log with token: {hmac_token}"
    findings = scanner.scan_text(text)
    assert len(findings) == 0


def test_positive_control_planted_leaks_found(tmp_path):
    canaries = generate_canaries(n=100, seed=42)
    scanner = LeakScanner(canaries)

    planted = canaries[:10]
    planted_lines = [
        f"Planting canary #{i}: {c.payer_phone} {c.email}" for i, c in enumerate(planted)
    ]
    decoy_file = tmp_path / "planted_leaks.log"
    decoy_file.write_text("\n".join(planted_lines))

    findings = scanner.scan_file(decoy_file)
    found_ids = {f.canary_id for f in findings}

    for c in planted:
        assert c.canary_id in found_ids


def test_negative_control_decoys_yield_zero_hits():
    # Decoys never sent through system
    decoys = generate_decoys(n=100, seed=999)

    # Simulate realistic app log with safe data
    system_log = """
    {"ts": 1729164000123, "decision": "ALLOW", "risk": "LOW", "server_ms": 14.2}
    {"ts": 1729164001456, "decision": "BLOCK", "reason": "ACCOUNT_DRAIN", "server_ms": 19.8}
    """

    decoy_scanner = LeakScanner(decoys)
    findings = decoy_scanner.scan_text(system_log)
    assert len(findings) == 0
