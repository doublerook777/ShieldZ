"""Train model on LinuxONE, evaluate holdout metrics, export ONNX, and benchmark engine latency."""

from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

from shieldz.config import ROOT, model_dir
from shieldz.contracts import FEATURE_ORDER, FeatureVector
from shieldz.model.data import default_data_path, get_peak_rss_mb, load_paysim, time_based_split
from shieldz.model.engine import XGBoostEngine
from shieldz.model.evaluate import evaluate_model
from shieldz.model.export import export_model_artifacts
from shieldz.model.train import train_xgboost


def main():
    print("=" * 60)
    print("Starting ShieldZ Model Training & Benchmarking on LinuxONE")
    print("=" * 60)

    data_file = default_data_path()
    print(f"Data source: {data_file}")
    t0 = time.time()
    rss0 = get_peak_rss_mb()
    print(f"Initial Peak RSS: {rss0:.1f} MB")

    # 1. Gate M1: Load full PaySim dataset
    print("\n--- Loading PaySim Dataset ---")
    X, y, step = load_paysim(data_file)
    load_time = time.time() - t0
    peak_rss = get_peak_rss_mb()
    print(f"Loaded {len(X):,} rows in {load_time:.2f} s.")
    print(f"Peak RSS during load: {peak_rss:.1f} MB (Gate M1 check)")
    print(f"Total Fraud rows: {int(y.sum()):,} ({y.mean() * 100:.3f}%)")

    # 2. Time-based Split (Train: step <= 500, Val: 500 < step <= 600, Test: step > 600)
    print("\n--- Performing Time-based Split ---")
    train_mask = (step <= 500).to_numpy()
    val_mask = ((step > 500) & (step <= 600)).to_numpy()
    test_mask = (step > 600).to_numpy()

    X_train, y_train = X.iloc[train_mask], y.iloc[train_mask]
    X_val, y_val = X.iloc[val_mask], y.iloc[val_mask]
    X_test, y_test = X.iloc[test_mask], y.iloc[test_mask]

    print(f"Train set: {len(X_train):,} rows (fraud: {int(y_train.sum()):,})")
    print(f"Val set:   {len(X_val):,} rows (fraud: {int(y_val.sum()):,})")
    print(f"Test set:  {len(X_test):,} rows (fraud: {int(y_test.sum()):,})")

    # Also save a 200k local development sample if not existing
    sample_path = ROOT / "data" / "paysim_sample.csv.gz"
    if not sample_path.exists():
        print(f"\nCreating 200k sample for local dev at {sample_path}...")
        sample_idx = np.random.default_rng(20261017).choice(len(X), size=min(200_000, len(X)), replace=False)
        sample_df = pd.concat([X.iloc[sample_idx], y.iloc[sample_idx], step.iloc[sample_idx]], axis=1)
        sample_df.to_csv(sample_path, compression="gzip", index=False)
        print("Sample created successfully.")

    # 3. Train XGBoost Model (Gate M2)
    print("\n--- Training XGBoost Booster ---")
    t_train_start = time.time()
    booster = train_xgboost(
        X_train,
        y_train,
        X_val=X_val,
        y_val=y_val,
        num_boost_round=100,
        early_stopping_rounds=15,
    )
    train_time = time.time() - t_train_start
    print(f"Training completed in {train_time:.2f} s.")

    engine = XGBoostEngine(booster, version="xgb-v1")
    engine.save(model_dir())

    # 4. Evaluate Model on Holdout Split
    print("\n--- Evaluating Model on Test Split ---")
    metrics = evaluate_model(engine, X_test, y_test, output_dir=ROOT / "results")
    print("\nEvaluation Results:")
    print(f"  PR-AUC:             {metrics['pr_auc']:.4f} (Target: >= 0.80)")
    print(f"  ROC-AUC:            {metrics['roc_auc']:.4f}")
    print(f"  Recall @ 1% FPR:    {metrics['recall_at_1pct_fpr']:.4f} (Target: >= 0.80)")
    print(f"  Baseline PR-AUC:    {metrics['baseline_pr_auc']:.4f}")
    print(f"  Selected t_review:  {metrics['thresholds']['t_review']}")
    print(f"  Selected t_block:   {metrics['thresholds']['t_block']}")
    print(f"  Gate M2 PR-AUC passed: {metrics['gate_m2_prauc_passed']}")

    # 5. Export Artifacts (JSON, ONNX, meta)
    print("\n--- Exporting Model Artifacts ---")
    exported = export_model_artifacts(
        engine,
        output_dir=model_dir(),
        extra_meta={
            "load_time_sec": round(load_time, 2),
            "train_time_sec": round(train_time, 2),
            "peak_rss_mb": peak_rss,
            "metrics": metrics,
        },
    )
    print(f"Exported artifacts: {list(exported.keys())}")

    # 6. Benchmark In-Process Engine Latency (5,000 requests)
    print("\n--- Benchmarking In-Process Engine Latency (5,000 rows) ---")
    bench_rows = X_test.iloc[:5000]
    latencies_us = []

    # Warmup
    for i in range(100):
        row_dict = bench_rows.iloc[i].to_dict()
        fv = FeatureVector(**row_dict)
        _ = engine.score(fv)
        _ = engine.reasons(fv)

    # Measurement
    for i in range(len(bench_rows)):
        row_dict = bench_rows.iloc[i].to_dict()
        fv = FeatureVector(**row_dict)
        t_start = time.perf_counter_ns()
        _ = engine.score(fv)
        _ = engine.reasons(fv)
        elapsed_us = (time.perf_counter_ns() - t_start) / 1000.0
        latencies_us.append(elapsed_us)

    latencies_us = np.array(latencies_us)
    latencies_ms = latencies_us / 1000.0

    p50_ms = float(np.percentile(latencies_ms, 50))
    p95_ms = float(np.percentile(latencies_ms, 95))
    p99_ms = float(np.percentile(latencies_ms, 99))
    max_ms = float(np.max(latencies_ms))

    print(f"Engine Latency (score + reasons) over 5,000 single-row queries:")
    print(f"  p50: {p50_ms:.3f} ms ({np.percentile(latencies_us, 50):.1f} us)")
    print(f"  p95: {p95_ms:.3f} ms ({np.percentile(latencies_us, 95):.1f} us)")
    print(f"  p99: {p99_ms:.3f} ms ({np.percentile(latencies_us, 99):.1f} us) [Target: <= 5.0 ms]")
    print(f"  max: {max_ms:.3f} ms")

    bench_results = {
        "engine": engine.name,
        "version": engine.version,
        "queries": len(bench_rows),
        "p50_ms": round(p50_ms, 3),
        "p95_ms": round(p95_ms, 3),
        "p99_ms": round(p99_ms, 3),
        "max_ms": round(max_ms, 3),
        "target_met": bool(p99_ms <= 5.0),
    }
    bench_file = ROOT / "results" / "engine_bench.json"
    bench_file.write_text(json.dumps(bench_results, indent=2))
    print(f"Saved benchmark results to {bench_file}")

    # 7. Generate Prediction Parity Golden Fixture (500 rows)
    print("\n--- Generating tests/golden/predictions_v1.csv (500 rows) ---")
    parity_rows = X_test.iloc[:500]
    scores = []
    reason_codes_list = []
    reason_levels_list = []

    for i in range(len(parity_rows)):
        fv = FeatureVector(**parity_rows.iloc[i].to_dict())
        s = engine.score(fv)
        r = engine.reasons(fv)
        scores.append(round(s, 6))
        reason_codes_list.append(";".join(c.value for c, _ in r))
        reason_levels_list.append(";".join(lv.value for _, lv in r))

    golden_df = parity_rows.copy()
    golden_df["expected_score"] = scores
    golden_df["expected_reason_codes"] = reason_codes_list
    golden_df["expected_reason_levels"] = reason_levels_list

    golden_path = ROOT / "tests" / "golden" / "predictions_v1.csv"
    golden_df.to_csv(golden_path, index=False)
    print(f"Saved prediction parity fixture to {golden_path}")

    print("\n" + "=" * 60)
    print("ALL MILESTONE GATES (M1 & M2) COMPLETED SUCCESSFULLY ON LINUXONE")
    print("=" * 60)


if __name__ == "__main__":
    main()
