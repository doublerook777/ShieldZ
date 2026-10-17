"""Score -> decision. Thresholds come from `artifacts/model/thresholds.json` (written by M2)."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

from shieldz.config import thresholds_file
from shieldz.contracts import DecisionKind, FeatureVector, Level

# PaySim fraud is almost entirely "drain the account", so the model scores every other payment
# 0.03-0.05 whatever the amount or payee: no threshold can make an ordinary payment a REVIEW. This
# rule covers that case in the open: a first payment to a payee we have never seen, of at least this
# many rupees, is held for a two-step confirmation. `null` in thresholds.json turns it off.
DEFAULT_REVIEW_NEW_PAYEE_MIN = 5_000.0


@dataclass(frozen=True)
class Thresholds:
    t_review: float
    t_block: float
    review_new_payee_min: float | None = DEFAULT_REVIEW_NEW_PAYEE_MIN

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
    minimum = data.get("review_new_payee_min", DEFAULT_REVIEW_NEW_PAYEE_MIN)
    return Thresholds(
        t_review=float(data["t_review"]),
        t_block=float(data["t_block"]),
        review_new_payee_min=None if minimum is None else float(minimum),
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
) -> tuple[DecisionKind, Level, bool]:
    """Rule layer after the model. It can only raise ALLOW to REVIEW, never lower a decision.

    Returns (kind, risk, fired)."""
    limit = thresholds.review_new_payee_min
    if (
        kind == DecisionKind.ALLOW
        and limit is not None
        and features.payee_prior_inbound == 0
        and features.log_amount >= math.log1p(limit)
    ):
        return DecisionKind.REVIEW, _RISK[DecisionKind.REVIEW], True
    return kind, _RISK[kind], False
