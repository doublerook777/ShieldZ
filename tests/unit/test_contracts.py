import typing
from datetime import datetime

import pytest
from pydantic import ValidationError

from shieldz.contracts import (
    FEATURE_ORDER,
    Decision,
    DecisionKind,
    Engine,
    FeatureInput,
    FeatureVector,
    Level,
    PaymentRequest,
    Reason,
    ReasonCode,
    safe_errors,
)

VALID = dict(
    payer_name="Kamala Devi",
    payer_phone="+91 98765 43210",
    payer_account="5021 3344 7788",
    payee_name="Safe Account",
    payee_account="9001 2222 3333",
    memo="urgent RBI safety transfer",
    tx_type="TRANSFER",
    amount=48250.37,
    payer_balance_before=48300.0,
    timestamp=datetime(2026, 10, 17, 23, 5),
)


def test_valid_request_parses():
    req = PaymentRequest(**VALID)
    assert req.language == "EN"
    assert req.payee_balance_before is None


@pytest.mark.parametrize(
    "bad",
    [
        {"amount": -1},
        {"amount": 0},
        {"amount": float("nan")},
        {"amount": float("inf")},
        {"payer_balance_before": -5},
        {"tx_type": "WIRE"},
        {"payer_name": ""},
        {"surprise_field": "x"},
        {"timestamp": "not a date"},
    ],
)
def test_bad_requests_are_rejected(bad):
    with pytest.raises(ValidationError):
        PaymentRequest(**{**VALID, **bad})


def test_validation_error_does_not_echo_input():
    secret = "Rukmini-Venkataraghavan-SECRET"
    with pytest.raises(ValidationError) as exc:
        PaymentRequest(**{**VALID, "tx_type": secret, "amount": secret, "memo": secret * 20})
    assert secret not in str(exc.value)
    safe = safe_errors(exc.value)
    assert {e["loc"][0] for e in safe} == {"tx_type", "amount", "memo"}
    assert secret not in str(safe)


def test_repr_does_not_leak_pii():
    text = repr(PaymentRequest(**VALID))
    for value in ("Kamala", "98765", "5021", "9001", "RBI", "Safe Account"):
        assert value not in text


def test_models_are_immutable():
    req = PaymentRequest(**VALID)
    with pytest.raises(ValidationError):
        req.amount = 1.0


def test_feature_vector_has_only_numeric_fields():
    for name, field in FeatureVector.model_fields.items():
        assert field.annotation in (int, float), f"{name} could hold free text"
    assert tuple(FeatureVector.model_fields) == FEATURE_ORDER


def test_feature_input_strings_are_only_tokens():
    hints = typing.get_type_hints(FeatureInput)
    text_fields = {n for n, t in hints.items() if t is str}
    assert text_fields == {"payee_token", "payer_token"}


def test_reason_code_enum_is_the_closed_set():
    assert {c.value for c in ReasonCode} == {
        "AMOUNT_HIGH_VS_BALANCE",
        "ACCOUNT_DRAIN",
        "NEW_RECIPIENT",
        "RISKY_TRANSFER_TYPE",
        "MULE_ACCOUNT_PATTERN",
        "LARGE_AMOUNT",
        "UNUSUAL_TIME",
        "OTHER_PATTERN",
    }


def test_decision_rejects_unknown_reason_code():
    base = dict(
        decision_id="d1",
        decision=DecisionKind.BLOCK,
        risk_level=Level.HIGH,
        model_version="v1",
        server_ms=3.2,
    )
    Decision(**base, reason_codes=[Reason(code=ReasonCode.ACCOUNT_DRAIN, level=Level.HIGH)])
    with pytest.raises(ValidationError):
        Decision(**base, reason_codes=[{"code": "Kamala Devi", "level": "HIGH"}])


def test_engine_protocol_accepts_a_stub():
    class Stub:
        name = "stub"
        version = "0"

        def score(self, features):
            return 0.0

        def reasons(self, features):
            return []

    assert isinstance(Stub(), Engine)
    assert not isinstance(object(), Engine)
