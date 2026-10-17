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
    args = parser.parse_args()

    print(f"🐤 Running ShieldZ Canary Leak Audit (env={args.env}, n={args.canaries})...")
    scorecard = run_leak_audit(
        runtime_dir=Path(args.runtime_dir),
        n_canaries=args.canaries,
        environment=args.env,
        results_dir=Path(args.results_dir),
    )

    print("\n" + scorecard.to_markdown())

    if scorecard.status == "PASS":
        print(f"\n🎉 Leak Audit PASSED: 0 leaks across {scorecard.sinks_scanned} sinks!")
        return 0
    else:
        print(f"\n❌ Leak Audit FAILED: {len(scorecard.findings)} leaks detected.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
