"""PaySim data loader, memory profiling, and time-based train/test splitting.

Post-transaction columns (newbalanceOrig, newbalanceDest) and isFlaggedFraud are
explicitly excluded from loading to prevent data leakage (ADR D12).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Tuple

import numpy as np
import pandas as pd

from shieldz.contracts import FEATURE_ORDER
from shieldz.features.engineer import FRAME_INPUT_COLUMNS, engineer_frame

# Standard PaySim columns we actually use. Banned post-transaction columns are never read.
PAYSIM_USE_COLS = [
    "step",
    "type",
    "amount",
    "nameOrig",
    "oldbalanceOrg",
    "nameDest",
    "oldbalanceDest",
    "isFraud",
]

PAYSIM_DTYPES = {
    "step": "uint16",
    "type": "category",
    "amount": "float32",
    "oldbalanceOrg": "float32",
    "oldbalanceDest": "float32",
    "isFraud": "uint8",
}


def get_peak_rss_mb() -> float:
    """Return peak Resident Set Size (RSS) in megabytes."""
    try:
        import resource

        # Linux reports in KB, Darwin/macOS in bytes
        rusage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        import sys

        if sys.platform == "darwin":
            return round(rusage / (1024.0 * 1024.0), 2)
        return round(rusage / 1024.0, 2)
    except (ImportError, AttributeError):
        pass

    try:
        import psutil

        proc = psutil.Process(os.getpid())
        return round(proc.memory_info().rss / (1024.0 * 1024.0), 2)
    except (ImportError, Exception):
        return 0.0


def default_data_path() -> Path:
    """Locate paysim data in data/ directory (either .parquet or .csv.gz or .csv)."""
    base = Path(__file__).resolve().parents[3] / "data"
    candidates = [
        base / "financial_txns.parquet",
        base / "paysim1.csv.gz",
        base / "paysim.csv.gz",
        base / "PS_20174392719_1491204439457_log.csv",
        base / "paysim1.csv",
    ]
    for c in candidates:
        if c.exists():
            return c
    return base / "paysim1.csv.gz"


def load_raw_df(path: Path | str | None = None, nrows: int | None = None) -> pd.DataFrame:
    """Load raw transactions with minimal memory footprint."""
    p = Path(path) if path is not None else default_data_path()
    if not p.exists():
        raise FileNotFoundError(f"PaySim data file not found at: {p}")

    suffix = p.name.lower()
    if suffix.endswith(".parquet"):
        try:
            import fastparquet

            pf = fastparquet.ParquetFile(str(p))
            # fastparquet to_pandas allows columns selection
            cols = [c for c in PAYSIM_USE_COLS if c in pf.columns]
            df = pf.to_pandas(columns=cols)
            if nrows is not None:
                df = df.iloc[:nrows]
        except Exception:
            df = pd.read_parquet(p, columns=PAYSIM_USE_COLS)
            if nrows is not None:
                df = df.iloc[:nrows]
    else:
        df = pd.read_csv(
            p,
            usecols=PAYSIM_USE_COLS,
            dtype=PAYSIM_DTYPES,
            nrows=nrows,
        )

    return df


def prepare_features(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series, pd.Series]:
    """Engineer features matching `FRAME_INPUT_COLUMNS` and `engineer_frame`.

    Returns:
        (X, y, step) where X has columns in FEATURE_ORDER.
    """
    # Payee merchant flag from PaySim nameDest prefix 'M'
    payee_merchant = df["nameDest"].astype(str).str.startswith("M").to_numpy(dtype=bool)

    # Payee balance before: For merchants, balance is unknown in PaySim (represented as NaN)
    old_dest = df["oldbalanceDest"].to_numpy(dtype=np.float64)
    payee_balance = np.where(payee_merchant, np.nan, old_dest)

    # Prior inbound transactions count calculated chronologically
    prior_inbound = df.groupby("nameDest").cumcount().to_numpy(dtype=np.int64)

    # Hour of day derived from simulation step (each step is 1 hour)
    hour = (df["step"].to_numpy(dtype=np.int64) % 24)

    frame_inputs = pd.DataFrame(
        {
            "tx_type": df["type"].astype(str),
            "amount": df["amount"].to_numpy(dtype=np.float64),
            "payer_balance_before": df["oldbalanceOrg"].to_numpy(dtype=np.float64),
            "payee_balance_before": payee_balance,
            "payee_is_merchant": payee_merchant,
            "hour_of_day": hour,
            "payee_prior_inbound": prior_inbound,
        },
        index=df.index,
    )

    X = engineer_frame(frame_inputs)
    y = pd.Series(df["isFraud"].to_numpy(dtype=np.int64), index=df.index, name="isFraud")
    step = pd.Series(df["step"].to_numpy(dtype=np.int64), index=df.index, name="step")
    return X, y, step


def load_paysim(
    path: Path | str | None = None, nrows: int | None = None
) -> Tuple[pd.DataFrame, pd.Series, pd.Series]:
    """Load PaySim dataset, transform to model features, and return (X, y, step)."""
    df = load_raw_df(path=path, nrows=nrows)
    return prepare_features(df)


def time_based_split(
    X: pd.DataFrame,
    y: pd.Series,
    step: pd.Series,
    split_step: int = 600,
) -> Tuple[pd.DataFrame, pd.Series, pd.DataFrame, pd.Series]:
    """Split into train (step <= split_step) and test (step > split_step).

    PaySim spans 743 steps (~30 days). Step 600 is ~Day 25, creating an ~80/20
    chronological split that reflects real-world model deployment without future leakage.
    """
    train_mask = (step <= split_step).to_numpy()
    test_mask = ~train_mask

    X_train = X.iloc[train_mask].copy()
    y_train = y.iloc[train_mask].copy()
    X_test = X.iloc[test_mask].copy()
    y_test = y.iloc[test_mask].copy()

    return X_train, y_train, X_test, y_test
