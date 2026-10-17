from shieldz.leak_audit.canaries import generate_canaries, generate_decoys


def test_generate_canaries_deterministic():
    batch1 = generate_canaries(n=10, seed=42)
    batch2 = generate_canaries(n=10, seed=42)
    assert len(batch1) == 10
    assert batch1 == batch2


def test_generate_canaries_fields():
    canaries = generate_canaries(n=50, seed=42)
    for c in canaries:
        assert c.canary_id.startswith("CANARY-")
        assert len(c.payer_phone.replace(" ", "").replace("+91", "")) == 10
        assert len(c.payer_account) == 12
        assert len(c.payee_account) == 12
        assert "@" in c.upi_id
        assert "@" in c.email
        assert c.memo.startswith("CANARY-")
        assert c.amount > 0
        assert c.payer_balance_before >= c.amount
        sensitive = c.get_sensitive_strings()
        assert c.payer_name in sensitive
        assert c.payer_phone in sensitive
        assert c.payer_account in sensitive


def test_decoys_do_not_overlap():
    canaries = generate_canaries(n=100, seed=42)
    decoys = generate_decoys(n=100, seed=999)
    canary_accounts = {c.payer_account for c in canaries}
    decoy_accounts = {d.payer_account for d in decoys}
    assert canary_accounts.isdisjoint(decoy_accounts)
