"""CLI entry point for Canary Leak Audit.

Usage:
    python -m shieldz.leak_audit [--env local|linuxone] [--runtime-dir artifacts/runtime]
"""

import argparse
import sys
from pathlib import Path

from shieldz.leak_audit.replay import run_leak_audit


def main() -> int:
    parser = argparse.ArgumentParser(description="ShieldZ Canary Leak Audit Runner")
    parser.add_argument("--env", default="local", help="Execution environment (local or linuxone)")
    parser.add_argument(
        "--runtime-dir",
        default="artifacts/runtime",
        help="Path to runtime artifacts directory",
    )
    parser.add_argument(
        "--results-dir",
        default="results",
        help="Path to directory for saving scorecards",
    )
    parser.add_argument(
        "--canaries",
        type=int,
        default=1000,
        help="Number of canaries to replay (default: 1000)",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="replay through the real service (fills every sink) instead of the log-only stand-in",
    )
    args = parser.parse_args()

    print(f"🐤 Running ShieldZ Canary Leak Audit (env={args.env}, n={args.canaries})...")
    close = None
    pipeline_fn = None
    if args.live:
        from shieldz.service.live_replay import live_pipeline_fn

        pipeline_fn, close = live_pipeline_fn(Path(args.runtime_dir))
    try:
        scorecard = run_leak_audit(
            runtime_dir=Path(args.runtime_dir),
            pipeline_fn=pipeline_fn,
            n_canaries=args.canaries,
            environment=args.env,
            results_dir=Path(args.results_dir),
        )
    finally:
        if close:
            close()

    print("\n" + scorecard.to_markdown())

    if scorecard.status == "PASS":
        print(f"\n🎉 Leak Audit PASSED: 0 leaks across {scorecard.sinks_scanned} sinks!")
        return 0
    else:
        print(f"\n❌ Leak Audit FAILED: {len(scorecard.findings)} leaks detected.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
