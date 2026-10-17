"""Canary Replay Engine for ShieldZ.

Replays synthetic canaries through the platform and coordinates the
end-to-end Leak Audit, positive controls, negative controls, and scorecard generation.
"""

from __future__ import annotations

import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

from shieldz.leak_audit.canaries import generate_canaries, generate_decoys
from shieldz.leak_audit.scanner import LeakScanner
from shieldz.leak_audit.scorecard import LeakScorecard
from shieldz.leak_audit.sinks import SinkRegistry


class StubService:
    """Minimal standalone stub simulating the ShieldZ stripped pipeline for M4 testing."""

    def __init__(self, log_path: Path) -> None:
        self.log_path = log_path
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def process(self, request_dict: dict[str, Any]) -> dict[str, Any]:
        """Simulates stripping PII and writing an allowlisted safe log."""
        # Simulated strip: PII dropped, accounts tokenized
        import hmac

        acc_token = hmac.new(
            b"test_pepper_key", request_dict["payer_account"].encode(), "sha256"
        ).hexdigest()

        # Write safe log line (Invariant I4: allowlisted fields only)
        import json

        safe_log = {
            "req_id": request_dict["request_id"],
            "tx_type": request_dict["tx_type"],
            "payer_token": acc_token,
            "decision": "ALLOW",
        }
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(safe_log) + "\n")

        return {"decision": "ALLOW", "risk": "LOW", "payer_token": acc_token}


def run_leak_audit(
    runtime_dir: Path | str = "artifacts/runtime",
    pipeline_fn: Callable[[dict[str, Any]], Any] | None = None,
    n_canaries: int = 1000,
    n_decoys: int = 1000,
    environment: str = "local",
    results_dir: Path | str = "results",
) -> LeakScorecard:
    """Executes a full Canary Leak Audit.

    1. Generates 1,000 canaries + 1,000 negative control decoys.
    2. Plants 10 canaries in a temporary decoy sink (Positive Control).
    3. Pushes canaries through `pipeline_fn` (or StubService if None).
    4. Scans all sinks with the canary scanner.
    5. Scans all sinks with the decoy scanner (Negative Control).
    6. Produces and saves the scorecard.
    """
    runtime_path = Path(runtime_dir)
    runtime_path.mkdir(parents=True, exist_ok=True)

    # 1. Generate canaries and decoys
    canaries = generate_canaries(n=n_canaries, seed=42)
    decoys = generate_decoys(n=n_decoys, seed=999)

    # Setup sink registry
    sinks = SinkRegistry(runtime_dir=runtime_path)
    sinks.register_default_sinks()

    # 2. Setup pipeline (stub if none provided)
    app_log = runtime_path / "logs" / "app.jsonl"
    if pipeline_fn is None:
        stub = StubService(log_path=app_log)
        pipeline_fn = stub.process

    # 3. Positive control: plant 10 canaries in a known decoy file
    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".log") as tmp:
        pos_control_file = Path(tmp.name)
        planted_canaries = canaries[:10]
        for c in planted_canaries:
            tmp.write(f"TEST_LEAK: {c.payer_phone} {c.email} {c.memo}\n")

    # 4. Replay canaries through pipeline
    captured_responses: list[str] = []
    for c in canaries:
        res = pipeline_fn(c.to_payment_request_dict())
        if isinstance(res, (str, bytes)):
            captured_responses.append(res.decode() if isinstance(res, bytes) else res)
        elif isinstance(res, dict):
            import json

            captured_responses.append(json.dumps(res))

    # Register captured HTTP responses as an in-memory sink
    sinks.register_custom("http_responses", lambda: "\n".join(captured_responses))

    # 5. Build scanners
    scanner = LeakScanner(canaries)
    decoy_scanner = LeakScanner(decoys)

    # 6. Verify positive control
    pos_findings = scanner.scan_file(pos_control_file, sink_name="positive_control")
    pos_control_file.unlink(missing_ok=True)  # Clean up temporary test file
    pos_found_ids = {f.canary_id for f in pos_findings}
    positive_control_found = sum(1 for c in planted_canaries if c.canary_id in pos_found_ids)

    # 7. Scan all system sinks for actual leaks
    actual_findings, bytes_per_sink = sinks.scan_all(scanner)

    # 8. Negative control: verify 0 decoy hits across all sinks
    decoy_findings, _ = sinks.scan_all(decoy_scanner)
    negative_control_hits = len(decoy_findings)

    # 9. Create and save scorecard
    scorecard = LeakScorecard.create(
        environment=environment,
        records_replayed=n_canaries,
        bytes_per_sink=bytes_per_sink,
        findings=actual_findings,
        positive_control_planted=len(planted_canaries),
        positive_control_found=positive_control_found,
        negative_control_decoys=n_decoys,
        negative_control_hits=negative_control_hits,
    )
    scorecard.save(out_dir=results_dir)

    return scorecard
