"""Score -> decision. Thresholds come from `artifacts/model/thresholds.json` (written by M2)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from shieldz.config import thresholds_file
from shieldz.contracts import DecisionKind, Level


@dataclass(frozen=True)
class Thresholds:
    t_review: float
    t_block: float

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
    return Thresholds(t_review=float(data["t_review"]), t_block=float(data["t_block"]))


def decide(score: float, thresholds: Thresholds) -> tuple[DecisionKind, Level]:
    """The risk level is a function of the decision, so the exact score never leaves the engine."""
    if score >= thresholds.t_block:
        kind = DecisionKind.BLOCK
    elif score >= thresholds.t_review:
        kind = DecisionKind.REVIEW
    else:
        kind = DecisionKind.ALLOW
    return kind, _RISK[kind]
