"""Train XGBoost model on decision-time PaySim features.

Uses tree_method='hist' for fast histogram-based training, scale_pos_weight for class
imbalance, and time-based train/validation splitting.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import pandas as pd

from shieldz.config import model_dir
from shieldz.contracts import FEATURE_ORDER
from shieldz.model.data import get_peak_rss_mb, load_paysim
from shieldz.model.engine import XGBoostEngine


def train_xgboost(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_val: pd.DataFrame | None = None,
    y_val: pd.Series | None = None,
    num_boost_round: int = 100,
    early_stopping_rounds: int = 15,
    custom_params: dict[str, Any] | None = None,
) -> Any:
    """Train XGBoost booster using histogram algorithm and class weighting."""
    import xgboost as xgb

    pos = int(y_train.sum())
    neg = int(len(y_train) - pos)
    scale_pos_weight = float(neg / max(pos, 1))

    params: dict[str, Any] = {
        "max_depth": 6,
        "learning_rate": 0.1,
        "tree_method": "hist",
        "objective": "binary:logistic",
        "eval_metric": ["aucpr", "auc"],
        "scale_pos_weight": scale_pos_weight,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "seed": 20261017,
        "nthread": 0,  # use all available vCPUs for training
    }
    if custom_params:
        params.update(custom_params)

    dtrain = xgb.DMatrix(
        X_train[list(FEATURE_ORDER)], label=y_train, feature_names=list(FEATURE_ORDER)
    )

    evals = [(dtrain, "train")]
    if X_val is not None and y_val is not None:
        dval = xgb.DMatrix(
            X_val[list(FEATURE_ORDER)], label=y_val, feature_names=list(FEATURE_ORDER)
        )
        evals.append((dval, "val"))

    evals_result: dict[str, dict[str, list[float]]] = {}
    booster = xgb.train(
        params,
        dtrain,
        num_boost_round=num_boost_round,
        evals=evals,
        early_stopping_rounds=early_stopping_rounds if X_val is not None else None,
        evals_result=evals_result,
        verbose_eval=10,
    )
    booster.evals_result_ = evals_result  # per-round metrics, kept for the training notebook's plots
    return booster


def run_training_pipeline(
    data_path: Path | str | None = None,
    output_dir: Path | str | None = None,
    nrows: int | None = None,
    val_split_step: int = 500,
    test_split_step: int = 600,
) -> tuple[XGBoostEngine, dict[str, Any]]:
    """Complete training pipeline: load data -> time split -> train -> save."""
    out_dir = Path(output_dir) if output_dir is not None else model_dir()
    out_dir.mkdir(parents=True, exist_ok=True)

    t0 = time.time()
    print("Loading data...")
    X, y, step = load_paysim(path=data_path, nrows=nrows)
    t_load = time.time() - t0
    peak_rss = get_peak_rss_mb()
    print(f"Loaded {len(X):,} rows in {t_load:.1f} s. Peak RSS: {peak_rss:.1f} MB.")

    # Time-based splitting
    # Train: step <= val_split_step
    # Val: val_split_step < step <= test_split_step
    # Test: step > test_split_step
    train_mask = (step <= val_split_step).to_numpy()
    val_mask = ((step > val_split_step) & (step <= test_split_step)).to_numpy()
    test_mask = (step > test_split_step).to_numpy()

    X_train, y_train = X.iloc[train_mask], y.iloc[train_mask]
    X_val, y_val = X.iloc[val_mask], y.iloc[val_mask]
    X_test, y_test = X.iloc[test_mask], y.iloc[test_mask]

    print(
        f"Split sizes: Train={len(X_train):,} (fraud={y_train.sum():,}), "
        f"Val={len(X_val):,} (fraud={y_val.sum():,}), "
        f"Test={len(X_test):,} (fraud={y_test.sum():,})"
    )

    t1 = time.time()
    print("Training XGBoost booster...")
    booster = train_xgboost(X_train, y_train, X_val=X_val, y_val=y_val)
    t_train = time.time() - t1
    print(f"Booster trained in {t_train:.1f} s.")

    engine = XGBoostEngine(booster, version="xgb-v1")
    engine.save(out_dir)
    print(f"Saved model to {out_dir}")

    info = {
        "train_rows": len(X_train),
        "val_rows": len(X_val),
        "test_rows": len(X_test),
        "train_fraud": int(y_train.sum()),
        "test_fraud": int(y_test.sum()),
        "load_time_sec": round(t_load, 2),
        "train_time_sec": round(t_train, 2),
        "peak_rss_mb": peak_rss,
    }
    return engine, info
