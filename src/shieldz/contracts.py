"""The shared contract between the parts of ShieldZ. Frozen after the M1 gate.

Only `PaymentRequest` can hold personal data, and only `privacy.strip()` may receive it (I1).
Everything else is numbers or members of closed enums, so it cannot carry free text.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field, ValidationError


class TxType(StrEnum):
    """PaySim transaction types."""

    TRANSFER = "TRANSFER"
    CASH_OUT = "CASH_OUT"
    PAYMENT = "PAYMENT"
    CASH_IN = "CASH_IN"
    DEBIT = "DEBIT"


class DecisionKind(StrEnum):
    ALLOW = "ALLOW"
    REVIEW = "REVIEW"
    BLOCK = "BLOCK"


class Level(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class Language(StrEnum):
    EN = "EN"
    HI = "HI"
    TA = "TA"


class ExplanationSource(StrEnum):
    GRANITE = "granite"
    TEMPLATE = "template"


class ReasonCode(StrEnum):
    """Closed set (ARCHITECTURE §4). Prompt, template, audit log and UI use only these."""

    AMOUNT_HIGH_VS_BALANCE = "AMOUNT_HIGH_VS_BALANCE"
    ACCOUNT_DRAIN = "ACCOUNT_DRAIN"
    NEW_RECIPIENT = "NEW_RECIPIENT"
    RISKY_TRANSFER_TYPE = "RISKY_TRANSFER_TYPE"
    MULE_ACCOUNT_PATTERN = "MULE_ACCOUNT_PATTERN"
    LARGE_AMOUNT = "LARGE_AMOUNT"
    UNUSUAL_TIME = "UNUSUAL_TIME"
    OTHER_PATTERN = "OTHER_PATTERN"


# Validation errors must never echo the offending value: it may be PII (API gate M3).
_BASE = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)
_MAX_MONEY = 1e12


def safe_errors(exc: ValidationError) -> list[dict]:
    """Field path and error type only. `exc.json()` / `exc.errors()` include the input value by
    default, so the API's 422 handler must use this instead."""
    return [{"loc": list(e["loc"]), "type": e["type"]} for e in exc.errors(include_input=False)]


class PaymentRequest(BaseModel):
    """What the bank app sends. The only model that holds PII."""

    model_config = _BASE

    # PII: repr=False so an accidental `print(req)` or log of the object doesn't leak it
    payer_name: str = Field(min_length=1, max_length=120, repr=False)
    payer_phone: str = Field(min_length=4, max_length=24, repr=False)
    payer_account: str = Field(min_length=3, max_length=64, repr=False)
    payee_name: str = Field(min_length=1, max_length=120, repr=False)
    payee_account: str = Field(min_length=3, max_length=64, repr=False)
    memo: str = Field(default="", max_length=500, repr=False)
    family_contact: str | None = Field(default=None, max_length=120, repr=False)

    tx_type: TxType
    amount: float = Field(gt=0, le=_MAX_MONEY, allow_inf_nan=False)
    payer_balance_before: float = Field(ge=0, le=_MAX_MONEY, allow_inf_nan=False)
    payee_balance_before: float | None = Field(
        default=None, ge=0, le=_MAX_MONEY, allow_inf_nan=False
    )
    payee_is_merchant: bool = False
    timestamp: datetime  # only the hour of day survives strip(), as sent by the caller
    language: Language = Language.EN


class FeatureInput(BaseModel):
    """`strip()` output. No names, phone, memo or raw account ids; tokens are keyed HMACs."""

    model_config = _BASE

    tx_type: TxType
    amount: float
    payer_balance_before: float
    payee_balance_before: float | None
    payee_is_merchant: bool
    hour_of_day: int = Field(ge=0, le=23)
    payee_token: str
    payer_token: str
    language: Language


class FeatureVector(BaseModel):
    """Model input. Numbers only, by construction (a test asserts every field is int or float)."""

    model_config = _BASE

    type_TRANSFER: int
    type_CASH_OUT: int
    type_PAYMENT: int
    type_CASH_IN: int
    type_DEBIT: int
    log_amount: float
    amount_to_balance: float
    drains_account: int
    payee_is_merchant: int
    payee_prior_inbound: int  # bucket: 0 = none, 1 = 1-3, 2 = 4 or more
    payee_balance_before_zero: int  # 1 only if the payee balance is known and zero
    hour_of_day: int


# Column order the model is trained and served with.
FEATURE_ORDER: tuple[str, ...] = tuple(FeatureVector.model_fields)


class Reason(BaseModel):
    model_config = _BASE

    code: ReasonCode
    level: Level


class Decision(BaseModel):
    """API response. No PII and no exact score (I5)."""

    model_config = _BASE

    decision_id: str
    decision: DecisionKind
    risk_level: Level
    reason_codes: list[Reason]
    model_version: str
    server_ms: float


class ExplainJob(BaseModel):
    """What the outbox hands to the explainer: codes, levels and language only."""

    model_config = _BASE

    decision_id: str
    decision: DecisionKind
    risk_level: Level
    reasons: list[Reason]
    language: Language


class Explanation(BaseModel):
    """The explainer's result, served by GET /v1/explanations/{decision_id}."""

    model_config = _BASE

    decision_id: str
    text: str
    source: ExplanationSource
    language: Language
    ts: str  # RFC 3339 UTC, set once by the writer; the journal records it as is


class AuditEntry(BaseModel):
    """One line of audit/chain.jsonl. `hash` covers every other field (canonical JSON)."""

    model_config = _BASE

    seq: int = Field(ge=0)
    ts: str  # RFC 3339 UTC
    decision_id: str
    decision: DecisionKind
    risk_level: Level
    reason_codes: list[Reason]
    model_version: str
    prev_hash: str
    hash: str


class AuditCheckpoint(BaseModel):
    """Signed chain head. One signature covers every entry up to `seq` (ADR D6)."""

    model_config = _BASE

    seq: int = Field(ge=0)
    head_hash: str
    ts: str
    signature: str  # hex


@runtime_checkable
class Engine(Protocol):
    """Hand-off between the model (LinuxONE operator) and the service (main build)."""

    name: str
    version: str

    def score(self, features: FeatureVector) -> float:
        """Fraud probability in [0, 1]. Stays in memory; never logged or returned."""
        ...

    def reasons(self, features: FeatureVector) -> list[tuple[ReasonCode, Level]]:
        """Up to three (code, level) pairs, strongest first. Deterministic."""
        ...
