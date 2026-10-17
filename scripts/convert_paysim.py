"""Convert downloaded financial_txns.parquet to paysim1.csv.gz on LinuxONE."""

from __future__ import annotations

import time
from pathlib import Path

import fastparquet

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
src = DATA_DIR / "financial_txns.parquet"
dst = DATA_DIR / "paysim1.csv.gz"

if not src.exists():
    print(f"Source {src} does not exist.")
    raise SystemExit(1)

print(f"Reading {src} with fastparquet...")
t0 = time.time()
pf = fastparquet.ParquetFile(str(src))
df = pf.to_pandas()
t_load = time.time() - t0
print(f"Loaded {len(df):,} rows in {t_load:.1f} s.")
print("Columns:", list(df.columns))

print(f"Saving to {dst} with gzip compression...")
t1 = time.time()
df.to_csv(dst, compression="gzip", index=False)
t_save = time.time() - t1
size_mb = dst.stat().st_size / 1e6
print(f"Successfully wrote {dst} ({size_mb:.1f} MB) in {t_save:.1f} s.")

src.unlink()
print(f"Removed temporary {src}.")
