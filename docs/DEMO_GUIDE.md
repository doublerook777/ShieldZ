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

The page is one column and follows the data. The title is **ShieldZ**. The page itself does not show the platform; show `s390x` from the **Platform** row of the Privacy check card, and from `curl localhost:8000/healthz` or `uname -m` on the VM.

**1. The payment.** Pick one of four payments (**Scam transfer**, **Electricity bill**, **Clinic payment**, **Large transfer**); the form fills in. Every field carries a small tag saying what happens to it: *removed*, *hashed*, *number only* or *kept as a code*. That is the privacy design in one glance. Press **Screen payment**.

**2. The decision.** The large panel is the real-time result (a few ms):

| Payment | Panel | What to say |
|---|---|---|
| Scam transfer | Filled off-white panel, **Blocked**, reasons AMOUNT_HIGH_VS_BALANCE, MULE_ACCOUNT_PATTERN, ACCOUNT_DRAIN. | The decision never waits for the language model. |
| Electricity bill | Plain panel, **Allowed**, no reasons. | Normal payments cost the customer nothing. |
| Clinic payment | Plain panel, **Allowed**, no reasons. | Paying a new merchant is normal, so there is no extra step. ShieldZ only adds friction where the pattern is risky. |
| Large transfer | Outlined panel, **Held for review**, reasons NEW_RECIPIENT and LARGE_AMOUNT. | Half of her savings to a stranger at 11 PM. The model alone would allow it (it learned full drains), so a policy rule next to the model holds a first payment of 40% or more of the balance (ADR D17). |

The explanation shows the reviewed template text at once; the small line under it changes to "Written by the Granite language model" when Granite's wording replaces it (instantly if cached; in template-only mode it stays on the template). The family-guardian message is a **preview**; nothing is sent.

**3. What happened to the data.** The most important part for the privacy story:
- **What you typed** (left): each field, the value you entered, and what the system did with it (removed, hashed, or used as a number and not stored).
- **What the system kept** (right): the record read back from the audit trail through `GET /v1/records/{decision_id}`: decision id, decision, risk level, reason codes, model version, time, position and hash in the chain. Nothing in it identifies the customer or the amount.
- **Shown to the language model**: the exact prompt from the prompt journal (fixed text plus the reason codes, no digits, no customer data). It fills in when the explainer has run. In template-only mode, or for Hindi and Tamil, or for an Allowed payment, the box says no language model was used. **To show the real prompt on camera, run the explainer with Granite (`make z-up`, not `EXPLAINER=template`).**

**4. Proof.** Left card **Privacy check**: the saved result of the canary audit (PASS, 0 leaks, 11 places searched, planted canaries 10 of 10, never-sent decoys 0 of 1,000). It is a stored result, not re-run on page load. Right card **Tamper check**: press **Verify audit trail**; the server re-verifies the whole signed chain.

Decisions are shown by treatment, not colour: Blocked is a filled panel, Review has a heavy outline, Allowed is plain.

Each press of **Screen payment** uses a **fresh payee** automatically (once you pay someone they count as known, and the same story would score lower). The electricity board is the one seeded payee that is not renamed. The first press may take a few extra ms (cold caches); press once off camera.

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
- REVIEW comes from "the model plus a policy rule": the model learned full drains, so a large partial transfer to a new payee would slip through. Ordinary new-payee payments (a clinic bill) are not touched.
- Scenario A is an exact full drain: PaySim fraud is almost entirely account drains, and that is what the model learned (PR-AUC 0.994 on a time-based holdout, `results/model_metrics.json`).

Don't claim: accuracy on elderly users (PaySim has no demographics), real-money use, that Granite writes every explanation live, that the family message is sent (it is a preview), that Granite uses the Telum/NNPA accelerator (the CPU does the work; `nnpa` is merely present in `/proc/cpuinfo`), or that the model is the clever part (a depth-3 decision tree matches it: `results/baseline_comparison.md`).

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
| Large transfer is ALLOW | policy rule off, or that payee was paid before | check `review_new_payee_ratio` in `artifacts/model/thresholds.json` (`null` disables it); select the payment again (each press uses a fresh payee) |
| Scam transfer is REVIEW or ALLOW | the balance field was edited, or the model was started without its payee-balance input | select the payment again to reset the form (each press uses a fresh payee) |
| No Granite text after 40 s | explainer backlog or crashed | section 6 |
| Privacy check card empty | no `results/leak_scorecard_*.json` mounted | `make z-up` mounts `results/` read-only |
| Verify says invalid right after you tampered | you edited the live file | restore it from the backup; use the copy method above |
