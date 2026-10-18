"""Score -> decision. Thresholds come from `artifacts/model/thresholds.json` (written by M2)."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

from shieldz.config import thresholds_file
from shieldz.contracts import DecisionKind, FeatureVector, Level, ReasonCode

# PaySim fraud is almost entirely "drain the whole account", so the model scores a large PARTIAL
# transfer to a stranger at 0.03-0.15 (measured on the VM) and would allow it. Real scams often take
# half or more of someone's savings. This rule closes that gap and nothing else: a first payment to
# a payee we have never seen, of at least `review_new_payee_ratio` of the payer's balance and at
# least `review_new_payee_min_amount` rupees, is held for a two-step confirmation. Ordinary
# payments to new payees (a clinic, a shop) are untouched. A `null` ratio in thresholds.json turns
# the rule off.
DEFAULT_REVIEW_NEW_PAYEE_RATIO = 0.4
DEFAULT_REVIEW_NEW_PAYEE_MIN_AMOUNT = 10_000.0


@dataclass(frozen=True)
class Thresholds:
    t_review: float
    t_block: float
    review_new_payee_ratio: float | None = DEFAULT_REVIEW_NEW_PAYEE_RATIO
    review_new_payee_min_amount: float = DEFAULT_REVIEW_NEW_PAYEE_MIN_AMOUNT

    def __post_init__(self) -> None:
        if not 0.0 <= self.t_review <= self.t_block <= 1.0:
            raise ValueError("thresholds must satisfy 0 <= t_review <= t_block <= 1")


# Used when no trained model has written thresholds yet (stub engine scores are 0.02 or 0.95)
DEFAULT_THRESHOLDS = Thresholds(t_review=0.5, t_block=0.9)

_RISK = {
    DecisionKind.ALLOW: Level.LOW,
    DecisionKind.REVIEW: Level.MEDIUM,
    DecisionKind.BLOCK: Level.HIGH,
}


def load_thresholds(path: Path | None = None) -> Thresholds:
    path = path or thresholds_file()
    if not path.exists():
        return DEFAULT_THRESHOLDS
    data = json.loads(path.read_text())
    ratio = data.get("review_new_payee_ratio", DEFAULT_REVIEW_NEW_PAYEE_RATIO)
    return Thresholds(
        t_review=float(data["t_review"]),
        t_block=float(data["t_block"]),
        review_new_payee_ratio=None if ratio is None else float(ratio),
        review_new_payee_min_amount=float(
            data.get("review_new_payee_min_amount", DEFAULT_REVIEW_NEW_PAYEE_MIN_AMOUNT)
        ),
    )


def decide(score: float, thresholds: Thresholds) -> tuple[DecisionKind, Level]:
    """The risk level is a function of the decision, so the exact score never leaves the engine."""
    if score >= thresholds.t_block:
        kind = DecisionKind.BLOCK
    elif score >= thresholds.t_review:
        kind = DecisionKind.REVIEW
    else:
        kind = DecisionKind.ALLOW
    return kind, _RISK[kind]


def apply_policy(
    kind: DecisionKind, features: FeatureVector, thresholds: Thresholds
) -> tuple[DecisionKind, Level, list[tuple[ReasonCode, Level]]]:
    """Rule layer after the model. It can only raise ALLOW to REVIEW, never lower a decision.

    Returns (kind, risk, reasons); `reasons` is empty unless the rule fired."""
    ratio = thresholds.review_new_payee_ratio
    if (
        kind == DecisionKind.ALLOW
        and ratio is not None
        and features.payee_prior_inbound == 0
        and features.amount_to_balance >= ratio
        and features.log_amount >= math.log1p(thresholds.review_new_payee_min_amount)
    ):
        reasons = [
            (ReasonCode.NEW_RECIPIENT, Level.MEDIUM),
            (ReasonCode.LARGE_AMOUNT, Level.MEDIUM),
        ]
        return DecisionKind.REVIEW, _RISK[DecisionKind.REVIEW], reasons
    return kind, _RISK[kind], []
