"""Download PaySim dataset directly from Kaggle and prepare paysim1.csv.gz."""

import os
import shutil
import subprocess
import time
from pathlib import Path

import kagglehub

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Remove the broken parquet if present to avoid s390x endianness segfault
parquet_file = DATA_DIR / "financial_txns.parquet"
if parquet_file.exists():
    print(f"Removing {parquet_file} (parquet C extensions segfault on big-endian s390x)...")
    parquet_file.unlink()

print("Downloading 'ealaxi/paysim1' from Kaggle via kagglehub...")
t0 = time.time()
download_path = kagglehub.dataset_download("ealaxi/paysim1")
print(f"Downloaded in {time.time() - t0:.1f} s to: {download_path}")

# Find the csv file inside download_path
csv_files = list(Path(download_path).glob("*.csv"))
if not csv_files:
    raise FileNotFoundError(f"No CSV found in {download_path}")

raw_csv = csv_files[0]
print(f"Found CSV: {raw_csv} ({raw_csv.stat().st_size / 1e6:.1f} MB)")

dest_gz = DATA_DIR / "paysim1.csv.gz"
print(f"Compressing to {dest_gz}...")
t1 = time.time()

# Use gzip subprocess for fast compression
with open(raw_csv, "rb") as f_in:
    with subprocess.Popen(["gzip", "-c"], stdin=subprocess.PIPE, stdout=open(dest_gz, "wb")) as proc:
        shutil.copyfileobj(f_in, proc.stdin)
        proc.stdin.close()
        proc.wait()

print(f"Compression complete in {time.time() - t1:.1f} s. Result: {dest_gz} ({dest_gz.stat().st_size / 1e6:.1f} MB)")
print("PaySim Kaggle download and setup complete!")
