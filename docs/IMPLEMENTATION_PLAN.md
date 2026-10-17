# ShieldZ — Implementation Plan

*Privacy-preserving, real-time scam and fraud defense for vulnerable users, built on IBM LinuxONE.*
IBM Z Datathon 2026 · Theme 2 "AI Secured: Innovation Without Exposure".

This file is the plan: what we build, in what order, and the checks each step must pass before the next one starts.
Related docs:

| Doc | What it holds |
|---|---|
| [ARCHITECTURE.md](ARCHITECTURE.md) | System architecture, data flow, invariants, file structure |
| [GLOSSARY.md](GLOSSARY.md) | Every technical term used in these docs, in plain language |
| [GIT_WORKFLOW.md](GIT_WORKFLOW.md) | Branches, commits, PRs, tags, what never gets committed |
| [LINUXONE_RUNBOOK.md](LINUXONE_RUNBOOK.md) | How to sync code to the LinuxONE VM, build and run containers, open Jupyter |
| [DECISIONS.md](DECISIONS.md) | Why we chose each tool, and what we changed from the original idea |
| [../progress.md](../progress.md) | Live status: the first thing to read when picking up work |
| [../explanation.md](../explanation.md) | Plain-language notes from each member/agent session |
| [../monkey_brain.md](../monkey_brain.md) | The whole project explained simply, with diagrams (good for onboarding and the video script) |

---

## 1. What we are building (one paragraph)

When a payment request arrives, ShieldZ removes personal data from it, scores it with an XGBoost model and answers **allow / review / block in under 50 ms (p99)** on LinuxONE. The top three reasons behind the score are turned into fixed **reason codes** such as `AMOUNT_HIGH_VS_BALANCE`. A separate worker later passes **only those codes** to IBM Granite, which writes a calm, plain-language warning for the user or a family member. Every decision goes into a **hash-chained, signed audit log**. The headline feature is the **Canary Leak Audit**. It pushes 1,000 fake identities through the whole system and proves, with a measured scorecard, that none of their details reached the LLM, the logs or any stored file.

---

## 2. How we develop: local-first, gated on LinuxONE

**Decision (final): write and unit-test code locally, then run every milestone's gate on LinuxONE before the milestone counts as done.** We do not wait until the end to "upload and check".

Why:
- LinuxONE is **s390x and big-endian**, and several popular packages have no s390x build (onnxruntime, shap and cryptography have no s390x wheels on PyPI; see [DECISIONS.md](DECISIONS.md)). Code that works on a laptop can fail on Z. Checking at every gate catches this within hours, not at the deadline.
- Day-to-day coding is much faster locally: instant tests, a local AI agent and no SSH lag.
- The judges score *use of LinuxONE*. Training, the latency benchmark, Granite, the final Leak Audit and all video evidence **must** run on LinuxONE anyway.

### The loop

```
 laptop (x86, Python 3.12 venv)            GitHub              LinuxONE VM (s390x)
 ───────────────────────────────           ──────              ──────────────────────────────
 code + unit tests on a data sample  ──push──▶ branch ──pull──▶  ~/shared/ShieldZ (git clone)
 make test  (fast, every change)                                 make z-gate   (at every milestone gate)
                                                                 Jupyter :38888 sees the same folder
 results/ committed from laptop  ◀────────── scp results/ back ──  results/*.json  (bench, metrics, scorecards)
```

| Work | Where it runs | Why |
|---|---|---|
| Writing code, unit tests, small-sample training | Laptop | Fast iteration |
| Full PaySim training (6.3M rows) | LinuxONE, from a Jupyter notebook that imports `shieldz` | Evidence for judges; model built on Z |
| Decision service + explainer containers | LinuxONE (Docker) | The product runs on Z |
| Granite explainer | LinuxONE (llama.cpp in the L1CC image) | Lab 2 stack; the laptop uses a template stand-in |
| Latency benchmark | LinuxONE, client on the same VM | The <50 ms claim must be measured on Z |
| Leak Audit | Laptop (template explainer) **and** LinuxONE (real Granite) | Fast feedback locally; official scorecard on Z |
| Demo recording | LinuxONE, browser through an SSH tunnel | Evidence |

Rules that keep the two environments in agreement:
1. The local venv uses **Python 3.12 and the same versions** that the LinuxONE image ships (xgboost 3.4.1, numpy 2.0.2, pandas 3.0.6, scikit-learn 1.9.0, onnx 1.22.0). They are pinned in `requirements/`.
2. **No new dependency without an s390x check.** Before adding a package, `python scripts/check_deps.py <pkg>` must show that it has an s390x wheel, is pure Python, or is already in the L1CC image. Record it in the dependency table in [DECISIONS.md](DECISIONS.md).
3. Models are saved as **XGBoost JSON** and data as **CSV(.gz)**. Do not pickle models across machines, and do not use parquet (pyarrow is not in the image).
4. Notebooks contain **no business logic**. They import from `src/shieldz` so that the same code is tested locally and run on Z.
5. The VM is **pull-only** for code. Nobody edits code on the VM. Results are copied back with `scp` and committed from a laptop.

---

## 3. Team roles (4 members, hybrid model)

We use a **hybrid** setup:
- The critical path (where each step needs the previous one) is **one build passed between members like a relay baton**.
- Around it, the other members work **in parallel in their own folders**. Those folders only meet the main build at the frozen contracts (`contracts.py`, after the M1 gate).

This avoids the idle time of a pure relay and the merge conflicts of four people coding in one fresh repo.

| Role | Default holder | Owns | Edits only these files/folders | Milestones |
|---|---|---|---|---|
| **Main build** (the baton) | Member 1 | Critical path: skeleton → contracts → features → decision service → integration | `contracts.py`, `config.py`, `privacy/`, `features/`, `service/app.py`, `service/decide.py`, `outbox/`, `containers/`, `Makefile`, `pyproject.toml`, `requirements/` (+ their tests) | M0 skeleton, M1 (except task 6), M3, M7 integration |
| **Proof build** | Member 2 | The parts that *prove* the privacy claim | `leak_audit/`, `audit/`, `explainer/prompt.py`, `explainer/guard.py`, `explainer/template.py`, `explainer/journal.py` (+ their tests) | M4, M6, M5 (prompt, guard, template) |
| **LinuxONE operator** | Member 3 | The model, plus everything that runs on the VM, so the builders never wait on it | `model/` (loader, training, evaluation, engine, reasons, export), `scripts/`, `notebooks/`, `explainer/granite.py`, `explainer/worker.py`, `results/` | M0 spikes, M1 task 6, **M2 (all of it)**, every Z gate, M5 (Granite + worker), benchmarks, evidence |
| **Pitch & review** | Member 4 | The story, and a second pair of eyes | `README.md`, `docs/assets/`, `service/static/`, `scripts/demo_scenarios.py` | Pitch research from 16:00, PR reviews, M7 demo UI, M8 lead, night relief for the main build |

Rules:
- The **main-build baton has exactly one holder at a time**, named in the `progress.md` status snapshot. Only the holder edits main-build files.
- Need a change in a file you don't own? Ask its owner, or open a small PR and tag them. Shared files (`Makefile`, `pyproject.toml`, `requirements/`) change only through the main-build holder.
- Any member can run a Z gate by following [LINUXONE_RUNBOOK.md](LINUXONE_RUNBOOK.md); Member 3 is the default.
- At **feature freeze (05:30)** everyone switches to M8.

### Handoff (baton or any role): tokens running out, sleep or away
1. **Giver:** commit and push the branch (a `wip` commit is fine). If `make test` is green and the task is complete, merge it.
2. **Giver:** update the `progress.md` snapshot ("Main build: Member X → Member Y, branch …, next step …"), add a log entry, and add an `explanation.md` section.
3. **Giver:** post in the team chat: "Baton → Member Y" (or "Proof build → …").
4. **Receiver:** `git pull`, read `progress.md` and the newest `explanation.md` entry, run `make test`, then confirm by editing the holder row in `progress.md`. Allow 20 minutes for this.

### Sleep and relief schedule (suggested; adjust at kick-off)

| Time (IST) | Awake | Main build (baton) | Proof build | Z gates / VM | Asleep |
|---|---|---|---|---|---|
| Sat 16:00 → 00:30 | all | Member 1 | Member 2 | Member 3 | — |
| 00:30 → 04:00 | 2, 4 | **Member 4** | Member 2 | Member 2 | 1, 3 |
| 04:00 → 07:00 | 1, 3 | **Member 1** | **Member 3** | Member 3 | 2, 4 |
| 07:00 → 10:00 | all | M8: everyone; video led by Member 4, submit by 09:30 | | | — |

Feature freeze (05:30) falls in the 04:00 → 07:00 shift. From then on, Members 1 and 3 capture evidence (screenshots, final `results/`) while Member 4's video script waits ready from the night before.

## 4. Roadmap

**Time box: Sat 17 Oct 16:00 IST → Sun 18 Oct 10:00 IST (18 hours, overnight).** All times below are IST. The hours are a budget, not a promise. If a milestone overruns by more than 50%, apply the cut order (§6) straight away. Waiting costs more.

```
Sat 16:00 18:00 20:00 22:00 Sun 00:00 02:00 04:00 06:00 08:00 10:00
    |─M0─|
        |─M1─|
          |───M2───|
            |────M3────|
        |(stub)──────M4───────|
                     |────M5────|
            |(lib)──────M6────────|
                                |──M7──|
F: stats, script, storyboard ──────────|────M8────|▲ submit 09:30
                                       ▲ feature freeze 05:30
```

Because we have 18 hours rather than 24, two cuts are **pre-applied**: post-quantum signing and the Snap ML comparison happen only if M4 has passed by 01:00.

**Overnight shifts.** Nobody codes well for 18 hours straight. Agree on sleep shifts at kick-off (e.g. half the team rests 01:00–04:30, the other half 04:30–07:00), so that M4, M5 and M6 always have an owner awake. Every shift change is a handoff: follow the protocol in [AGENTS.md](../AGENTS.md).

Dependency rule: **a milestone may start once the gates of the milestones it depends on have passed.** The parallel roles can still prepare work against the M1 contracts and stubs before then.

```
M0 ─▶ M1 ─┬─▶ M2 ─▶ M3 ─┬─▶ M4 (final) ─┐
          │             └─▶ M5 ─▶ M4 rerun ├─▶ M7 ─▶ M8
          ├─▶ M4 (against stub service)  │
          └─▶ M6 (library only) ─────────┘
```

Every gate has two halves:
- **Local gate:** `make test` (plus any milestone-specific command) is green on a laptop.
- **Z gate:** `make z-gate` on the LinuxONE VM is green, and the numbers are written to `results/` and logged in `progress.md`.

A gate passes only if **every** box is ticked. Then tag `main` with `mN-gate` (see [GIT_WORKFLOW.md](GIT_WORKFLOW.md)).

---

### M0 — Platform spikes and scaffolding (16:00 → 17:30) · all members

**Goal:** remove every s390x unknown before writing real code, and create the repo skeleton.

Tasks
1. **VM facts** (on the VM; record each answer in `progress.md` → "LinuxONE facts"): (OS = Ubuntu 24.04-Datathon and Docker 29.8.0 are already confirmed) `nproc`, `free -h`, `df -h ~`, `uname -m`, whether `/proc/cpuinfo` lists `nnpa`, Python version inside the Jupyter container (`/opt/venv/bin/python --version`).
2. **Base image check:** build a throwaway image `FROM registry.linuxone.cloud.marist.edu/l1cc/jupyterlab-image-s390x:latest` that runs `pip install fastapi uvicorn faker pytest`. It must succeed. fastapi, uvicorn, faker and pytest are pure Python, and pydantic-core has a cp312 s390x wheel.
3. **Granite location:** inside the Jupyter container, find the Lab 2 model: `find / -name "*.gguf" 2>/dev/null`, then read how `loan_demo/rag_utils.py:load_model` opens it (context size, threads). **Read only; do not copy code (event rules).** Load it with `llama_cpp.Llama`, generate 60 tokens and record the model name, quantization and tokens/second.
4. **Signing library spike (timebox 30 min, ADR D6).** Try these in order and stop at the first that works:
   - (a) `docker exec notebook cat /etc/os-release`. If the image is Debian/Ubuntu-based, run `apt-get install -y python3-cryptography` in the throwaway image and make it visible to `/opt/venv` with a `.pth` file pointing at `/usr/lib/python3/dist-packages` (same Python 3.12 ABI).
   - (b) `pip install cryptography`, building from source with `rustc cargo libssl-dev`.
   - (c) Our own RFC 8032 Ed25519.

   Record which one worked.
5. **Snap ML spike (timebox 20 min):** `pip install snapml` (cp312 s390x wheel exists). Record whether it imports.
6. **Data:** download PaySim from Kaggle on a laptop (`ealaxi/paysim1`), check its licence and record it in README credits, then `scp` the zip to `~/shared/ShieldZ/data/` on the VM. Also make a 200k-row stratified sample for local work, kept in `data/` and gitignored.
7. **Repo skeleton** (Main build): the directory tree from [ARCHITECTURE.md §7](ARCHITECTURE.md#7-file-structure), `pyproject.toml`, `requirements/*.txt`, `Makefile`, `.gitignore` entries (`data/`, `artifacts/`, `*.gguf`, `.venv/`, keys), `pytest.ini` with markers `z`, `llm`, `slow`, one smoke test, `scripts/z_doctor.py`, `scripts/check_deps.py`.
8. Local venv: `uv venv --python 3.12 && uv pip install -r requirements/local-dev.txt`.

**Gate M0** (tag `m0-gate`)
- [ ] `make test` green locally (smoke test).
- [ ] `python scripts/z_doctor.py` on the VM prints OK for: s390x, Python 3.12, `import xgboost, numpy, pandas, sklearn, onnx, llama_cpp`, versions equal to `requirements/z-preinstalled.txt`, and a writable `~/shared/ShieldZ/artifacts`.
- [ ] Throwaway image with the extras builds on the VM.
- [ ] Granite generates text on the VM; model file and tokens/second recorded.
- [ ] Results of the cryptography and Snap ML spikes recorded; ADRs D2 and D6 marked *Accepted* with the outcome.
- [ ] PaySim is on the VM, and its licence is recorded in the README.
- [ ] "LinuxONE facts" section of `progress.md` filled in.
- [ ] `df -h ~` shows ≥ 10 GB free before any image build (prune first if not).

---

### M1 — Contracts and feature pipeline (17:00 → 19:00) · Main build

**Goal:** freeze the shared data shapes so that the parallel roles can work independently, and build the one feature function that both training and serving use.

Tasks
1. `src/shieldz/contracts.py`: an `Engine` protocol (`score(FeatureVector) -> float`, `reasons(FeatureVector) -> list[(ReasonCode, Level)]`) that is the hand-off point between the model (Member 3) and the service (Member 1). Plus Pydantic models `PaymentRequest` (includes PII: payer name, phone, account, payee account and name, amount, balances, free-text `memo`), `FeatureVector` (no PII by construction), `Decision`, `ReasonCode` enum (closed set, see [ARCHITECTURE.md §4](ARCHITECTURE.md#4-reason-codes)), `Level` enum (`LOW/MEDIUM/HIGH`), `ExplainJob`, `AuditEntry`.
2. `privacy/tokenize.py`: HMAC-SHA256 tokenization of account identifiers with a secret pepper loaded from `artifacts/keys/pepper` (generated on first run, never committed).
3. `privacy/strip.py`: `strip(PaymentRequest) -> (FeatureInput, tokens)`. This is the **only** function that touches PII. Names, phone and memo are dropped here.
4. `features/engineer.py`: `engineer(FeatureInput, history) -> FeatureVector`. It is used by training (batch over a DataFrame) and by serving (one row), from the same code path.
5. `features/history.py`: recipient-novelty store keyed by HMAC tokens (in memory, with an optional SQLite snapshot).
   - **Seeded at startup** from PaySim's inbound counts and from `src/shieldz/features/demo_seed.csv` (fake demo payees with a normal history), so a cold start doesn't flag every payee as new.
   - The count is bucketed (0 / 1–3 / 4+), so training and serving see the same scale.
6. *(LinuxONE operator)* `model/data.py`: PaySim loader with dtypes (keeps memory low), **time-based split** on `step` (train on the earlier steps, test on later ones), drop `isFlaggedFraud`.
7. Use **decision-time features only** (the table in [ARCHITECTURE.md §3](ARCHITECTURE.md#3-request-lifecycle-decision-path)). PaySim's post-transaction balances are unknown before a real payment executes, so training on them would be **data leakage**.

**Gate M1** (tag `m1-gate`)
- [ ] Unit tests: contracts validate and reject bad input; `FeatureVector` has no field that can hold free text (test asserts that all fields are numeric or enum).
- [ ] **PII barrier test:** `strip()` output, serialized, contains none of the input's name, phone, account, memo or exact amount strings.
- [ ] Feature unit tests on hand-made rows (account drain, mule-account pattern, new recipient).
- [ ] Test that the feature list contains **no post-transaction column** (`newbalanceOrig`, `newbalanceDest` or anything derived from them).
- [ ] Cold-start test: a fresh history store with the seed loaded puts the demo bill-payment payee in the `4+` bucket.
- [ ] **Parity test:** `tests/golden/features_v1.csv` (200 rows → expected features) gives identical results locally and on the VM (`make z-gate`).
- [ ] Loader on the VM reads the full PaySim within memory limits (peak RSS recorded).
- [ ] Contracts reviewed by Members 2, 3 and 4, then marked **frozen** in `progress.md`. After this, changing them needs a PR that every member acknowledges.

---

### M2 — Model, thresholds and reason codes (18:30 → 22:00) · LinuxONE operator

**Goal:** a trained, evaluated model on Z, with fast per-transaction explanations.

Tasks
1. `model/train.py`: XGBoost `hist` booster with `scale_pos_weight` for the class imbalance and early stopping on a validation split. Train on a sample locally; **train on full PaySim on LinuxONE** via `notebooks/02_train_on_linuxone.ipynb` (evidence).
2. `model/evaluate.py`: PR-AUC, ROC-AUC, recall at a fixed false-positive rate, and a confusion matrix at the chosen thresholds. Write `results/model_metrics.json` and a short `results/MODEL_CARD.md` that states the synthetic data, the missing demographics and the PaySim limitations.
3. Thresholds: choose `t_review` and `t_block` on the validation set (e.g. block when precision ≥ 0.95, review when recall ≥ 0.95). Store them in `artifacts/model/thresholds.json`. The main build's `service/decide.py` only reads this file.
4. `model/reasons.py`: XGBoost `pred_contribs=True` (exact TreeSHAP, built into XGBoost) → top-3 features with **positive** contribution → `(ReasonCode, Level)` through a fixed mapping table. Raw values are discarded.
   - A feature becomes a code only if its contribution is ≥ `MIN_CONTRIB` (start at +0.1 log-odds and tune). If no feature qualifies, use `OTHER_PATTERN`.
   - Contributions are computed only for REVIEW/BLOCK.
   - Fallback if the 5 ms engine budget is missed: compute codes in the explainer worker from the numeric `FeatureVector` (no PII), and leave the request path with the decision only.
5. `model/engine.py`: an inference backend interface with `XGBoostEngine` (default; `inplace_predict`, `nthread=1` for single rows). Add `SnapMLEngine` only if M0 showed that Snap ML works.
6. `model/export.py`: save `model.json` (XGBoost JSON), `model.onnx` (via onnxmltools, checked with `onnx.checker`) and `model_meta.json` (feature order, thresholds, version, training data hash, git SHA). ONNX is the portable export; we do not serve it on Z (no onnxruntime for s390x; ADR D2).

**Gate M2** (tag `m2-gate`)
- [ ] Time-based holdout on the VM: target **PR-AUC ≥ 0.80** and **recall ≥ 0.80 at FPR ≤ 1%**. Tuning is timeboxed to **45 min**. If the target isn't met, the **floor** is PR-AUC ≥ 0.50 **and** beating a simple rule baseline (`TRANSFER/CASH_OUT` with `amount_to_balance ≥ 0.99`) on PR-AUC. Record the numbers and the exemption in `progress.md`.
- [ ] **Prediction parity:** `tests/golden/predictions_v1.csv` (500 rows) matches local vs Z within 1e-6, and the reason codes are identical.
- [ ] Reason codes are deterministic (same input → same codes, 100 repeats).
- [ ] Every reason code is one of the `ReasonCode` enum values (property test over 10k rows).
- [ ] In-process `predict + contribs` for one row on the VM: **p99 ≤ 5 ms** over 5,000 rows (`results/engine_bench.json`). If Snap ML exists, benchmark it too and keep the faster one.
- [ ] `model.onnx` passes `onnx.checker.check_model`.
- [ ] Model artifacts are copied to `~/shared/ShieldZ/artifacts/model/` on the VM. They are not committed; `model_meta.json` and the metrics are.

---

### M3 — Real-time decision service (19:00 → 23:30) · Main build

**Goal:** an HTTP service on LinuxONE that decides within 50 ms p99 and never writes PII.

Tasks
0. Until M2 lands, the service uses a **stub engine**: a simple rule (`TRANSFER/CASH_OUT` and `amount_to_balance ≥ 0.99`) behind the M1 `Engine` protocol. Swapping in the real `XGBoostEngine` is a one-line config change.
1. `service/app.py` (FastAPI): `POST /v1/score` → `Decision {decision_id, decision, risk_level, reason_codes, model_version, server_ms}`. The response contains no PII and no exact score. `GET /healthz` returns `platform` (from `uname -m`), the model version and the engine. Make the endpoint a plain `def` so FastAPI runs it in its thread pool and CPU-bound inference doesn't block the event loop.
2. Pipeline per request: validate → `strip()` → `engineer()` → engine predict → `decide()` → reasons (for REVIEW/BLOCK) → **audit append** (M6 stub until then) → **outbox enqueue** → respond.
3. `outbox/queue.py`: SQLite in WAL mode with `busy_timeout=5000`, table `explain_jobs(id, decision_id, decision, reason_codes, levels, language, status, created_at)`. The insert costs well under a millisecond. Both containers run the same image, so the same UID owns the files.
4. `privacy/redact_log.py`: JSON logging with a **field allowlist**: only known safe keys are logged and everything else is dropped. Uvicorn access logs are switched off (they would log paths and clients).
5. `containers/Containerfile`: `FROM` the L1CC jupyterlab image, `pip install -r requirements/z-extra.txt`, copy `src/`, with a default CMD that runs the API. One image provides two commands: `api` and `explainer`.
6. `scripts/bench_latency.py`: asyncio + httpx client **on the VM itself** (localhost). 500 warm-up requests, then 5,000 measured at concurrency 1 and 8. It records client p50/p95/p99 and server-side `server_ms` p50/p95/p99 in `results/latency_<tag>.json`.
7. Expose the API to laptops through an **SSH tunnel**, not a public port (ADR D8).

**Gate M3** (tag `m3-gate`)
- [ ] API contract tests (FastAPI TestClient): valid request → decision; invalid → 422 with no echo of input values.
- [ ] **Log PII test:** 50 requests with distinctive PII → captured log output contains none of it.
- [ ] Container builds and runs on the VM; `/healthz` reports `s390x`.
- [ ] **Latency on the VM: p99 < 50 ms** (client-measured, localhost) at concurrency 1 and 8. Store the results file and paste the numbers into `progress.md`.
- [ ] Each request writes one outbox row (count check after the benchmark).
- [ ] From a clean start (empty runtime dir, seed loaded): demo scenario (b), a normal bill payment, gives **ALLOW**.

---

### M4 — Canary Leak Audit (18:00 stub → 01:00) · Proof build · NEVER CUT

**Goal:** a repeatable test that proves no personal data reaches the LLM, the logs or storage, and that the scanner really would catch a leak.

Tasks
1. `leak_audit/canaries.py`: seeded Faker generates **1,000** records with Indian-locale names, +91 phone numbers, account numbers, UPI IDs, emails, a memo with a unique marker (`CANARY-<hex>`) and a **distinctive amount** (unusual paise values such as `48250.37`).
2. `leak_audit/sinks.py`: **registry of every place data lands.** It includes the app log file, container stdout/stderr (`docker logs`), the audit chain file, the SQLite outbox (all text columns), the prompt journal, LLM outputs (explanations table), HTTP responses captured by the replay client, the history store, and a **catch-all walk of the whole runtime directory** (`artifacts/runtime/**`). Any file nobody registered still gets scanned.
3. `leak_audit/scanner.py`: for every canary value it searches for the exact value plus **variants**: case-folded, whitespace/separator-stripped, digits-only, base64, hex, URL-encoded, and unsalted MD5/SHA-1/SHA-256 hex digests. A `PARTIAL` leak is a **standalone** run of 7 or more digits that appears inside a canary phone or account number. Standalone means bounded by non-digits, after joining digit groups split by spaces or dashes. Digits inside longer runs (timestamps, hashes, IDs) don't count, because that's where random collisions happen. HMAC tokens are allowed because they need the secret pepper to reverse.
4. `leak_audit/replay.py`: drives the canaries through the full pipeline, either in-process with TestClient (local, template explainer) or over HTTP against the running containers (VM, real Granite). It waits for the explainer queue to drain before scanning.
5. **Positive control:** `--plant-leak` writes 10 canaries into a decoy sink. The run is valid only if the scanner finds **exactly those 10**. Without this, "0 leaks" could just mean the scanner is broken.
   **Negative control:** generate 1,000 *decoy* canaries the same way but **never send them**, and search for them too. Any decoy hit is a false positive, meaning the matching rules are too loose. A valid run has 0 decoy hits.
6. `leak_audit/scorecard.py`: `results/leak_scorecard_<env>.json` and `.md` with records replayed, sinks scanned, bytes scanned, leaks and partials per sink, the positive-control result, git SHA, `uname -m` and timestamp. The scorecard is signed by the audit key once M6 lands.

Before M3 lands, the proof build develops and tests the scanner against a **stub service** (a few lines that call `strip()` and write to a log), so M4 isn't blocked.

**Gate M4** (tag `m4-gate`)
- [ ] Scanner unit tests: each variant type is detected when planted in a temp file; HMAC tokens are not flagged.
- [ ] Positive control: 10/10 planted canaries detected. Negative control: 0 hits for the 1,000 never-sent decoys.
- [ ] `make leak-audit` locally (template explainer): **0 leaks, 0 partials**, under 5 min.
- [ ] **On the VM against the running containers: 0 leaks, 0 partials**, scorecard in `results/`.
- [ ] Every sink type in [ARCHITECTURE.md §5](ARCHITECTURE.md#5-where-data-lands-sinks) appears in the scorecard with bytes scanned > 0.
- [ ] Re-run after M5 with real Granite (see the M5 gate).

---

### M5 — Granite explainer (22:30 → 02:30) · Proof build (prompt, guard) + LinuxONE operator (Granite, worker)

**Goal:** plain-language warnings written by Granite from reason codes only, without ever slowing the decision.

Tasks
1. `explainer/prompt.py`: builds prompts **only** from a fixed template plus `ReasonCode`/`Level`/`Decision`/`language` enum values and their fixed descriptions. No free text from the request can reach it.
2. `explainer/guard.py`: the **allowlist firewall** that runs before every LLM call.
   - It parses the job's enum values, **re-renders the template itself and requires the prompt to match byte for byte**. So no name, memo or other free text can slip in, with or without digits.
   - On top of that, the variable parts must contain **no digits**.
   - If any check fails, the call is refused and the worker uses the template.
   - The **output guard** rejects PII-shaped content: any run of 4+ digits, money amounts (₹/Rs/INR next to a number), phone-like patterns, URLs and `@`. Small numbers like "24 hours" or "3 steps" are allowed.
   - Every explanation records its `source` (`granite` or `template`), and the UI shows it.
3. `explainer/journal.py`: records every prompt and output (a registered Leak Audit sink).
4. `explainer/template.py`: `TemplateExplainer` (deterministic, human-written sentences per code; used locally and as the fallback; proof build). `explainer/granite.py`: `GraniteExplainer` (llama_cpp with the Lab 2 GGUF; thread count capped so it doesn't starve the API; LinuxONE operator).
5. `explainer/worker.py`: polls the SQLite outbox, explains, stores the result, marks the job done. It runs in its **own container**, CPU-pinned away from the API (`--cpuset-cpus`; see the runbook).
6. Languages: English from Granite. **Hindi/Tamil (stretch):** first test Granite's Hindi output. If it's weak, use human-reviewed static templates per reason code. Granite is not officially trained for Hindi or Tamil, so we check before relying on it.
7. `GET /v1/explanations/{decision_id}` for the demo UI to poll.

**Gate M5** (tag `m5-gate`)
- [ ] Guard tests: prompts with an injected digit, an injected name (letters only), an unknown code, extra text or an over-long length are **all rejected**; 1,000 fuzzed prompts → 0 accepted that break the rules.
- [ ] On the VM: an explanation appears for a BLOCK decision within the measured time (record p50 seconds).
- [ ] **Granite really writes the text:** on 50 sample BLOCK/REVIEW jobs on the VM, ≥ 80% of explanations have `source = granite`, not the template fallback. Record the rate.
- [ ] Cross-container outbox: 5,000 jobs written by `shieldz-api` and consumed by `shieldz-explainer` with 0 `database is locked` errors.
- [ ] **Latency isolation:** re-run the M3 benchmark **while the explainer is busy**; decision p99 is still **< 50 ms**.
- [ ] **Leak Audit re-run on the VM with real Granite: 0 leaks, 0 partials.**
- [ ] Three sample explanations (one per main scenario) saved in `results/sample_explanations.md` for the video.

---

### M6 — Tamper-evident audit trail (19:00 lib → 03:00) · Proof build

**Goal:** every decision is written to a log that cannot be quietly altered, and we can show that.

Tasks
1. `audit/chain.py`: append-only JSONL. Each entry `{seq, ts, decision_id, decision, risk_level, reason_codes, model_version, prev_hash}` gets `hash = SHA-256(canonical JSON)` (sorted keys, no spaces). The API runs one process, so an in-process lock serialises appends. The append (hash + write) takes microseconds and is the only audit work in the request path.
2. `audit/signing.py`: Ed25519 key pair in `artifacts/keys/` (private key never committed; public key exported to `results/audit_pubkey.pem`). Backend chosen in M0 (ADR D6). **Signing never runs in the request path.** A background thread signs a **checkpoint** (the chain head hash) every 100 entries or every second, whichever comes first. Because of the chain, one checkpoint signature covers every entry before it.
3. `audit/verify.py` CLI: recomputes the chain, checks every signature/checkpoint and reports the first broken `seq`.
4. **Stretch (90 min timebox, only if M3 to M5 gates have passed):** post-quantum ML-DSA (Dilithium) via liboqs on s390x. Drop it without regret if the build fails.

**Gate M6** (tag `m6-gate`)
- [ ] `verify` passes on a 10,000-entry chain generated on the VM.
- [ ] **Tamper tests:** changing one byte, deleting one line, swapping two lines → each one is detected at the exact `seq`.
- [ ] If using our own Ed25519: **all RFC 8032 §7.1 test vectors pass.**
- [ ] Audit append adds **≤ 1 ms p99** to the decision path (re-run the M3 benchmark; still < 50 ms).
- [ ] The audit file is a registered Leak Audit sink and passes the scan.

---

### M7 — Demo UI and end-to-end integration (02:30 → 05:30) · Main build + Pitch & review (UI)

**Goal:** one command brings up the full system on the VM, and a scripted demo tells the story.

Tasks
1. `service/static/`: a single HTML page served by FastAPI with a payment form, scenario buttons, an instant decision badge with its ms timing, an explanation panel that polls, a "family alert" panel, the Leak Audit scorecard viewer and an audit-chain verify button.
2. `scripts/demo_scenarios.py`: three scripted stories: (a) "digital arrest" scam (large transfer to a new recipient that drains the account) → BLOCK; (b) normal bill payment → ALLOW; (c) borderline case → REVIEW.
3. `make z-up` / `make z-down`: build the image, start the `api` and `explainer` containers with CPU pinning, show their health.

**Gate M7** (tag `m7-gate`)
- [ ] From a clean VM state: `make z-up` → all three scenarios give the expected decisions → explanations appear → `verify` passes → leak scorecard shows 0.
- [ ] Dress rehearsal of the demo through the SSH tunnel, timed.
- [ ] **Feature freeze at 05:30.** After this, only bug fixes and docs.

---

### M8 — Evidence, video and submission (05:30 → 09:30 submit; hard deadline 10:00) · everyone, led by Pitch & review

Tasks
1. Evidence screenshots in `docs/assets/evidence/`: `uname -m` → `s390x`, `docker ps` and `docker stats` with both containers, the Jupyter training notebook with outputs on LinuxONE, latency results, the leak scorecard, a tamper-detection run.
2. Export the architecture flowchart (Mermaid in ARCHITECTURE.md) to PNG for the optional upload.
3. README: final numbers, how to run, **credits with links for every dataset and library** (required by the rules).
4. Video **≤ 3:00**: problem and data (sourced statistics), solution, live demo, **how it uses IBM Z** (stack, LinuxONE instance, model), the leak-audit proof.
5. Submit on hack2skill. The title contains the team name: `[Team Name_IBM Z Datathon 2026 Project]`. Include the GitHub link.

**Gate M8 = submission checklist**
- [ ] Video ≤ 3:00 and covers all four required points.
- [ ] Repo public (or link accessible), README credits complete, no secrets/data/models committed (`git ls-files | grep -E 'keys|\.gguf|\.csv'` returns only the golden fixtures).
- [ ] Every number in the video matches a file in `results/`.
- [ ] Submitted before the deadline; confirmation screenshot in `progress.md`.

---

## 5. Test strategy summary

| Layer | Tool | Runs where | Marker |
|---|---|---|---|
| Unit tests | pytest | laptop + VM | (none) |
| Golden parity (features, predictions) | pytest + `tests/golden/` | both; compares outputs | (none) |
| Z-only tests (real image, Granite, full data) | pytest | VM only | `@pytest.mark.z`, `@pytest.mark.llm` |
| Latency | `scripts/bench_latency.py` | VM | — |
| Leak Audit | `python -m shieldz.leak_audit` | both | — |
| Audit integrity | `python -m shieldz.audit.verify` | both | — |

`make test` = `pytest -m "not z and not llm"`. `make z-gate` (on the VM, inside the container) = `pytest` (all markers) + `scripts/z_doctor.py` + whatever the current milestone's gate lists.

---

## 6. Cut order (if behind schedule)

Cut from the top first:
1. Post-quantum signing (ML-DSA/Dilithium).
2. Hindi/Tamil.
3. Snap ML engine comparison.
4. UI polish (keep a plain functional page).
5. ONNX export.

**Never cut:** the Leak Audit with its positive control, the latency benchmark on LinuxONE, the live demo, the video evidence.

---

## 7. Risks we already know about

| Risk | Mitigation |
|---|---|
| No onnxruntime/shap/cryptography wheels for s390x | Serve with XGBoost (or Snap ML); TreeSHAP via `pred_contribs`; Ed25519 fallback (ADRs D2, D3, D6) |
| VM memory too small for full PaySim | Load with explicit dtypes and `usecols`; if needed, train on all fraud rows plus a non-fraud sample and document it |
| Granite slow on CPU | It's asynchronous by design; cap its threads; template fallback keeps the UX working |
| CPU contention hurts p99 | Separate containers pinned to separate cores; benchmark while the explainer is busy (M5 gate) |
| Leak scanner false positives (random digit collisions) | Standalone-digit partial rule + negative control with never-sent decoys (M4) |
| Granite output always falling back to the template | Output guard targets PII shapes, not all digits; `source` recorded; ≥ 80% Granite gate (M5) |
| Cold-start history flags every payee as new | Seeded, bucketed history store; clean-start ALLOW test (M3) |
| Fewer than 4 vCPUs | `make z-up` computes the core split from `nproc` (runbook §5) |
| PaySim is "too easy" (post-transaction balance artifacts) | Decision-time features only; time-based split; model card states the limitation; we claim architecture, not real-world accuracy |
| Metric gate not met without the leaky columns | The gate allows a documented, team-agreed exception; honesty about the metric scores better than a leaky one |
| VM has no backups | Code lives in git; `results/` copied back to laptops after every gate; model can be retrained |
| A member or agent leaves mid-task | `progress.md` + `explanation.md` handoff protocol (see AGENTS.md) |
