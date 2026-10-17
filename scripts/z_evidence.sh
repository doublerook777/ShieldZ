#!/usr/bin/env bash
# Run on the VM host from the repo root, after `make z-up`. Produces the gate evidence that the
# benchmark file alone doesn't cover (M3/M5/M6/M7). Every output goes to results/.
#
#   bash scripts/z_evidence.sh            # about 25 min: Granite writes ~16 s per explanation
#   SAMPLES=10 bash scripts/z_evidence.sh # quick pass
set -u
cd "$(dirname "$0")/.."
IMAGE=${IMAGE:-shieldz:latest}
SAMPLES=${SAMPLES:-50}
RUN="docker run -i --rm --network host -v $PWD/artifacts:/app/artifacts -v $PWD/results:/app/results $IMAGE"
mkdir -p results
fail=0

echo "== 1. platform and signer backend"
curl -s localhost:8000/healthz | tee results/z_healthz.json; echo
docker logs shieldz-api 2>&1 | grep -E 'signer_backend|"startup"' | tee results/z_signer_backend.txt
grep -q '"status":"cryptography"' results/z_signer_backend.txt \
  || { echo "FAIL: signer is not 'cryptography' (pure Python costs ~250 ms per signature)"; fail=1; }
docker logs shieldz-explainer 2>&1 | grep -E 'worker_start|generator' | head -3

echo "== 2. demo scenarios (A BLOCK, B ALLOW, C REVIEW expected)"
$RUN python scripts/demo_scenarios.py --run 2>&1 | tee results/z_demo_run.txt
for want in "Instant Decision: BLOCK" "Instant Decision: ALLOW" "Instant Decision: REVIEW"; do
  grep -q "$want" results/z_demo_run.txt || { echo "FAIL: no '$want'"; fail=1; }
done

echo "== 3. latency with the explainer busy"
# The benchmark's own BLOCK/REVIEW decisions keep the explainer generating the whole time.
( for _ in 1 2 3 4 5 6; do docker stats --no-stream --format '{{.Name}} cpu={{.CPUPerc}} mem={{.MemUsage}}' \
    shieldz-api shieldz-explainer; sleep 10; done ) > results/z_busy_docker_stats.txt 2>&1 &
make bench TAG=busy || fail=1
$RUN python - <<'PY' | tee results/z_outbox_after_bench.txt
import sqlite3
db = sqlite3.connect("/app/artifacts/runtime/outbox.sqlite")
print("outbox status counts right after the benchmark (pending/running > 0 = explainer was busy):")
for status, n in db.execute("SELECT status, COUNT(*) FROM explain_jobs GROUP BY status"):
    print(f"  {status}: {n}")
PY
cat results/z_busy_docker_stats.txt

echo "== 4. drop the benchmark's backlog (Granite needs ~16 s per job), then sample Granite alone"
$RUN python -c "
from shieldz.outbox.queue import Outbox
print('dropped', Outbox('/app/artifacts/runtime/outbox.sqlite').skip_pending(), 'pending jobs')"
sleep 20   # let the job the worker already holds finish
$RUN python scripts/granite_sample.py --n "$SAMPLES" --timeout 3000 2>&1 | tee results/z_granite_sample.log
[ "${PIPESTATUS[0]}" -eq 0 ] || { echo "FAIL: Granite rate below 80% (see results/z_granite_sample.log)"; fail=1; }

echo "== 5. audit chain verification and append cost"
$RUN python -m shieldz.audit.verify artifacts/runtime/audit/chain.jsonl \
  --checkpoints artifacts/runtime/audit/checkpoints.jsonl --pubkey artifacts/keys/audit_pubkey.pem \
  2>&1 | tee results/audit_verify_linuxone.txt
grep -q "VERIFY PASS" results/audit_verify_linuxone.txt || { echo "FAIL: chain did not verify"; fail=1; }
$RUN python - <<'PY' | tee results/audit_append_bench.txt
import tempfile, time
from pathlib import Path
import numpy as np
from shieldz.audit import AuditChain
chain = AuditChain(Path(tempfile.mkdtemp()) / "chain.jsonl")
times = []
for i in range(5000):
    t = time.perf_counter()
    chain.append(f"{i:032x}", "BLOCK", "HIGH", [], "bench")
    times.append((time.perf_counter() - t) * 1000)
a = np.asarray(times)
print(f"AuditChain.append x5000 on {__import__('platform').machine()}: "
      f"p50 {np.percentile(a, 50):.3f} ms, p99 {np.percentile(a, 99):.3f} ms (gate: p99 <= 1 ms)")
PY

echo
[ $fail -eq 0 ] && echo "ALL EVIDENCE COLLECTED: commit results/ and tick the gates" \
                || echo "SOME CHECKS FAILED: read the FAIL lines above"
exit $fail
