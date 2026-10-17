# Demo guide: try it yourself, then record it

Everything here was run against the live LinuxONE VM (s390x) on 2026-10-18. Numbers quoted come from files in `results/`.

**The one-line story:** a payment screen that decides in milliseconds whether a transfer looks like a scam, explains why in plain words, and proves afterwards that it never leaked a customer's data and never edited its own history. All of it runs on IBM LinuxONE.

---

## 1. Connect (laptop, 1 minute)

You need the VM's SSH key loaded in your agent (`ssh-add <key>`; it asks for the passphrase once).

```bash
# a tunnel: the VM's port 8000 appears on your laptop (nothing is exposed publicly)
ssh -N -L 8000:localhost:8000 linux1@148.100.76.241
```
Leave it running (or add `-f` to background it). Then:

```bash
curl -s localhost:8000/healthz
# {"status":"ok","platform":"s390x","engine":"xgboost","model_version":"xgb-v1"}
```
`platform: s390x` is the point: it is the mainframe architecture answering. If you see `stub-rule`, the API was started without the model: run `make z-up` on the VM.

Open **http://localhost:8000/** in a browser.

## 2. Check the stack and warm the cache (VM, 3 minutes)

```bash
ssh linux1@148.100.76.241
cd ~/shared/ShieldZ
docker ps --format '{{.Names}}  {{.Status}}'      # shieldz-api, shieldz-explainer (+ notebook)
docker logs shieldz-api 2>&1 | grep signer_backend  # must say "cryptography" (the fast signer)
```

Granite needs about 11 s to write a fresh explanation. Explanations are cached by prompt, so generate the demo ones **before** you show it:

```bash
docker run -i --rm --network host shieldz:latest python scripts/prewarm_explanations.py
# lists each scenario, "Granite ready after N s", and "K of K distinct prompts cached"
```
If the explainer has a backlog (for example after a benchmark), drop it first, otherwise the newest job still waits behind the one being generated:
```bash
docker exec shieldz-api python -c "from shieldz.outbox.queue import Outbox; print(Outbox('/app/artifacts/runtime/outbox.sqlite').skip_pending())"
```

## 3. Walk through the UI (about 3 minutes)

The top of the page shows the platform and engine it read from `/healthz`.

| Click | What you should see | What to say |
|---|---|---|
| **Scenario A, Digital Arrest** card, then **Authorize & Screen Transaction** | **BLOCK**, a few ms, reasons AMOUNT_HIGH_VS_BALANCE, MULE_ACCOUNT_PATTERN, ACCOUNT_DRAIN. The explanation panel shows the template text at once, then switches to **IBM Granite** (instantly if cached). A family-alert **preview** appears (the message text is written per scenario; nothing is sent). | The decision never waits for the language model. The text on screen first is the reviewed template; Granite's wording replaces it when ready. |
| **Scenario B, Electricity Bill** | **ALLOW**, about 1-2 ms, no reasons, no explanation. | Normal payments cost the customer nothing. The utility has a long history in the seeded data. |
| **Scenario C, Clinic Payment** | **REVIEW**, reason NEW_RECIPIENT. A two-step confirmation, not a block. | A first payment of ₹5,000+ to an unknown payee is held by a **policy rule next to the model** (ADR D17). The model alone scores B and C identically. |
| Tab **Canary Leak Audit Scorecard**, **Refresh** | PASS, 0 exact / variant / partial leaks, 11 sinks, positive control 10/10, negative control 0 hits. | We planted fake customers with distinctive names, numbers and memos, sent them through, then searched every place data lands. They are nowhere. |
| Tab **Tamper-Evident Audit Chain**, verify button | "Chain valid", tens of thousands of entries, signatures valid. | Every decision is in a hash chain with signed checkpoints. |
| Tab **LinuxONE Topology** | The two containers and the core split. | API pinned to core 0, explainer to cores 1-2 (Granite runs on the CPU through llama.cpp; we do not claim accelerator use). |

Each scenario click uses a **fresh payee** automatically. (Once you pay someone, they count as known and the same story would score lower; that is correct behaviour, but it would make repeat takes differ.) The electricity board is the one seeded payee that is not renamed.

The first time you press the button the API may take a few extra ms (cold caches). Press once off camera.

## 4. Proof for the camera (VM)

```bash
uname -m                      # s390x
nproc                         # 3
docker ps                     # both containers up
docker stats --no-stream      # explainer CPU while Granite works, API idle
cat results/latency_busy.json | python3 -m json.tool | head -40   # p99 with the explainer busy
```
Numbers on file: p99 **6.9 ms** (concurrency 1) and **21.8 ms** (concurrency 8) idle (`results/latency_real.json`); **11.5 / 23.4 ms** with Granite generating (`results/latency_busy.json`). Limit: 50 ms.

### Tamper demo (30 seconds, safe: works on a copy)
```bash
cd ~/shared/ShieldZ && mkdir -p /tmp/tamper
cp artifacts/runtime/audit/chain.jsonl artifacts/runtime/audit/checkpoints.jsonl /tmp/tamper/
V="docker run --rm -v /tmp/tamper:/t:ro -v $PWD/artifacts/keys:/k:ro shieldz:latest python -m shieldz.audit.verify /t/chain.jsonl --checkpoints /t/checkpoints.jsonl --pubkey /k/audit_pubkey.pem"
$V                                                              # VERIFY PASS: ... entries verified OK
sed -i '1001s/"decision":"ALLOW"/"decision":"BLOCK"/' /tmp/tamper/chain.jsonl   # change one past decision
$V                                                              # VERIFY FAIL (seq 1000): Hash mismatch ...
cp artifacts/runtime/audit/chain.jsonl /tmp/tamper/chain.jsonl; sed -i '500d' /tmp/tamper/chain.jsonl
$V                                                              # VERIFY FAIL (seq 500): Sequence break ...
```
Never edit `artifacts/runtime/audit/chain.jsonl` itself; the API appends to it.

## 5. What to say, and what not to claim

Say:
- Granite 350M explains **why**, in **English**. The "what to do" sentence ("call your bank on the official number on your card") and the **Hindi and Tamil** texts are human-written templates, because the small model answers in English whatever language it is asked for and, left alone, told customers to call "their number" (the scammer's).
- Granite texts are generated **once per reason combination and cached**; the first request pays about 11 s (the template shows meanwhile).
- Fresh Granite generation on the VM: p50 10.4 s; 28 of 30 distinct prompts passed the quality guard (`results/granite_quality.md`).
- REVIEW comes from "the model plus a policy rule".
- Scenario A is an exact full drain: PaySim fraud is almost entirely account drains, and that is what the model learned (PR-AUC 0.994 on a time-based holdout, `results/model_metrics.json`).

Don't claim: accuracy on elderly users (PaySim has no demographics), real-money use, that Granite writes every explanation live, that the family alert is sent (it is a message preview), or that Granite uses the Telum/NNPA accelerator (the CPU does the work; `nnpa` is merely present in `/proc/cpuinfo`).

## 6. Between takes

- **Back to the same state:** nothing to do. Fresh payee per click; ALLOW/BLOCK/REVIEW repeat.
- **Explanation stuck on the template:** the explainer is busy or down: `docker logs shieldz-explainer 2>&1 | tail`, then drop the backlog (section 2) or `docker restart shieldz-explainer`.
- **Fully clean runtime** (empties history, audit chain, outbox and the Granite cache; do it only after you have captured the evidence you need):
  ```bash
  make z-down && mv artifacts/runtime /tmp/runtime_backup_$(date +%s) && make z-up
  docker run -i --rm --network host shieldz:latest python scripts/prewarm_explanations.py
  ```

## 7. If something looks wrong

| Symptom | Likely cause | Fix |
|---|---|---|
| Page does not load | tunnel closed | rerun the `ssh -N -L` command |
| `/healthz` says `stub-rule` | api started without the model | `make z-up` (defaults to `ENGINE=xgboost`) |
| Scenario C is ALLOW | policy rule off, or that payee was paid before | check `review_new_payee_min` in `artifacts/model/thresholds.json`; reload the scenario card (new payee) |
| Scenario A is REVIEW or ALLOW | same payee already paid | reload the card |
| No Granite text after 40 s | explainer backlog or crashed | section 6 |
| Scorecard tab empty | no `results/leak_scorecard_*.json` mounted | `make z-up` mounts `results/` read-only |
| Verify says invalid right after you tampered | you edited the live file | restore it from the backup; use the copy method above |
