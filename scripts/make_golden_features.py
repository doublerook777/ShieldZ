"""Regenerate tests/golden/features_v1.csv (200 rows: inputs -> expected features).

Only run this when the feature definition changes on purpose; then review the diff. The test
compares laptop and LinuxONE results to this file, so a silent change fails loudly.
"""

from pathlib import Path

import numpy as np
import pandas as pd

from shieldz.contracts import TxType
from shieldz.features.engineer import FRAME_INPUT_COLUMNS, engineer_frame

OUT = Path(__file__).resolve().parent.parent / "tests" / "golden" / "features_v1.csv"


def make_inputs(n: int = 200, seed: int = 20261017) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    balance = np.round(rng.lognormal(9, 1.5, n), 2)
    frac = rng.choice([0.01, 0.1, 0.5, 0.9, 0.99, 1.0, 1.5], n)
    df = pd.DataFrame(
        {
            "tx_type": rng.choice([t.value for t in TxType], n),
            "amount": np.round(balance * frac, 2) + 0.01,
            "payer_balance_before": balance,
            "payee_balance_before": np.where(
                rng.random(n) < 0.3,
                np.nan,
                np.round(rng.lognormal(8, 2, n) * (rng.random(n) > 0.4), 2),
            ),
            "payee_is_merchant": rng.random(n) < 0.3,
            "hour_of_day": rng.integers(0, 24, n),
            "payee_prior_inbound": rng.choice([0, 0, 1, 2, 3, 4, 5, 40, 5000], n),
        }
    )
    # hand-made edge rows first: empty account, exact drain, zero balance, boundaries of the buckets
    edge = pd.DataFrame(
        [
            ("TRANSFER", 100.0, 100.0, 0.0, False, 3, 0),
            ("CASH_OUT", 50.0, 0.0, np.nan, False, 23, 1),
            ("PAYMENT", 1.0, 1e9, np.nan, True, 12, 4),
            ("DEBIT", 0.01, 0.0, 0.0, False, 0, 3),
        ],
        columns=list(FRAME_INPUT_COLUMNS),
    )
    return pd.concat([edge, df], ignore_index=True).head(n)


if __name__ == "__main__":
    inputs = make_inputs()
    expected = engineer_frame(inputs).add_prefix("expected_")  # input and feature names overlap
    pd.concat([inputs, expected], axis=1).to_csv(OUT, index=False)
    print(f"wrote {OUT} ({len(inputs)} rows)")
