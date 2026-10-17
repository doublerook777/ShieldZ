import json
import os
import stat
from datetime import datetime

import pytest

from shieldz.contracts import FeatureInput, PaymentRequest
from shieldz.privacy import Tokenizer, load_pepper, strip
from shieldz.privacy.tokenize import normalize_id

PII = dict(
    payer_name="Rukmini Venkataraghavan",
    payer_phone="+91 90031 47729",
    payer_account="7713 0042 9918",
    payee_name="Anand Subramaniam",
    payee_account="9001 2222 3333",
    memo="CANARY-7f3a9c urgent",
    family_contact="meena.k417@okbank",
)


def request(**over):
    base = dict(
        **PII,
        tx_type="TRANSFER",
        amount=48250.37,
        payer_balance_before=48300.0,
        timestamp=datetime(2026, 10, 17, 23, 5),
    )
    return PaymentRequest(**{**base, **over})


@pytest.fixture
def tok():
    return Tokenizer(b"0123456789abcdef0123456789abcdef")


def test_no_pii_in_output(tok):
    out = strip(request(), tok)
    text = json.dumps(out.model_dump(mode="json"))
    forbidden = [
        "Rukmini",
        "Venkataraghavan",
        "Anand",
        "Subramaniam",
        "90031",
        "47729",
        "7713",
        "0042",
        "9918",
        "771300429918",
        "9001",
        "2222",
        "3333",
        "900122223333",
        "CANARY",
        "7f3a9c",
        "urgent",
        "meena",
        "okbank",
    ]
    for item in forbidden:
        assert item not in text, item


def test_strip_keeps_only_what_features_need(tok):
    out = strip(request(payee_balance_before=0.0, payee_is_merchant=True), tok)
    assert isinstance(out, FeatureInput)
    assert out.tx_type == "TRANSFER"
    assert out.hour_of_day == 23
    assert out.payee_balance_before == 0.0
    assert out.payee_is_merchant is True


def test_tokens_are_stable_and_ignore_formatting(tok):
    a = strip(request(payee_account="9001 2222 3333"), tok).payee_token
    b = strip(request(payee_account="9001-2222-3333"), tok).payee_token
    c = strip(request(payee_account="9001 2222 3334"), tok).payee_token
    assert a == b
    assert a != c


def test_same_account_gets_same_token_as_payer_or_payee(tok):
    out = strip(request(payer_account="5555 6666 7777", payee_account="5555-6666-7777"), tok)
    assert out.payer_token == out.payee_token


def test_token_is_not_a_plain_hash_and_depends_on_pepper():
    import hashlib

    a = Tokenizer(b"A" * 32).token("900122223333")
    b = Tokenizer(b"B" * 32).token("900122223333")
    assert a != b
    assert a != hashlib.sha256(b"900122223333").hexdigest()[: len(a)]
    assert len(a) == 32


def test_empty_identifier_rejected():
    with pytest.raises(ValueError):
        normalize_id("--- ---")


def test_pepper_is_created_once_with_private_permissions(tmp_path):
    path = tmp_path / "keys" / "pepper"
    first = load_pepper(path)
    assert len(first) == 32
    assert stat.S_IMODE(os.stat(path).st_mode) == 0o600
    assert load_pepper(path) == first


def test_tokenizer_repr_hides_pepper():
    assert "AAAA" not in repr(Tokenizer(b"A" * 32))
