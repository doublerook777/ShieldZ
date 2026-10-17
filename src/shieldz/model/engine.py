"""Inference engines satisfying the contracts.Engine protocol.

Provides XGBoostEngine with fast in-process scoring (`inplace_predict`) and exact
TreeSHAP reason code extraction (`pred_contribs=True`).
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from shieldz.contracts import FEATURE_ORDER, FeatureVector, Level, ReasonCode
from shieldz.model.reasons import extract_reasons_from_contribs


class XGBoostEngine:
    """XGBoost inference engine implementing the contracts.Engine protocol."""

    name: str = "xgboost"
    version: str = "xgb-v1"

    def __init__(self, booster, version: str = "xgb-v1") -> None:
        self.booster = booster
        self.version = version
        # Configure single-thread prediction for real-time serving
        try:
            self.booster.set_param({"nthread": 1})
        except Exception:
            pass

    def _features_to_array(self, features: FeatureVector) -> np.ndarray:
        return np.array(
            [[getattr(features, col) for col in FEATURE_ORDER]],
            dtype=np.float32,
        )

    def score(self, features: FeatureVector) -> float:
        """Fraud probability in [0.0, 1.0]. Fast in-place predict."""
        arr = self._features_to_array(features)
        try:
            pred = self.booster.inplace_predict(arr)
            return float(pred[0])
        except Exception:
            import xgboost as xgb

            dmat = xgb.DMatrix(arr, feature_names=list(FEATURE_ORDER))
            pred = self.booster.predict(dmat)
            return float(pred[0])

    def reasons(self, features: FeatureVector) -> list[tuple[ReasonCode, Level]]:
        """Extract top (ReasonCode, Level) pairs using exact TreeSHAP contributions."""
        import xgboost as xgb

        arr = self._features_to_array(features)
        dmat = xgb.DMatrix(arr, feature_names=list(FEATURE_ORDER))
        # Returns shape (1, num_features + 1) where last column is bias
        contribs = self.booster.predict(dmat, pred_contribs=True)[0]
        return extract_reasons_from_contribs(features, contribs)

    def save(self, model_dir: Path | str) -> None:
        p = Path(model_dir)
        p.mkdir(parents=True, exist_ok=True)
        self.booster.save_model(str(p / "model.json"))
        meta = {
            "name": self.name,
            "version": self.version,
            "feature_order": list(FEATURE_ORDER),
        }
        (p / "model_meta.json").write_text(json.dumps(meta, indent=2))

    @classmethod
    def load(cls, model_dir: Path | str) -> XGBoostEngine:
        import xgboost as xgb

        p = Path(model_dir)
        model_file = p / "model.json"
        if not model_file.exists():
            raise FileNotFoundError(f"XGBoost model file not found: {model_file}")

        booster = xgb.Booster()
        booster.load_model(str(model_file))

        version = "xgb-v1"
        meta_file = p / "model_meta.json"
        if meta_file.exists():
            try:
                data = json.loads(meta_file.read_text())
                version = data.get("version", version)
            except Exception:
                pass

        return cls(booster, version=version)
