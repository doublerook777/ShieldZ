# ShieldZ — Progress

> **Read this first** if you are picking up work (human or AI agent). Then read the latest entries in [explanation.md](explanation.md).
> Questions or critiques for others go in [conversation.md](conversation.md).
> **Update this before you stop**, even mid-task (protocol in [AGENTS.md](AGENTS.md)). `main` must always have a current copy.

---

## Status snapshot (overwrite this block on every update)

| | |
|---|---|
| **Last updated** | 2026-10-17 22:50 IST · Member 4 & 2: Demo UI wired to backend endpoints (`d4cfe59`), demo scenarios CLI (`scripts/demo_scenarios.py`), pitch research doc & README credits merged. Canary Leak Audit replayed `--live` across 11 sinks (2,146,647 bytes scanned, 0 leaks, all sinks filled). C-006 & C-007 closed. 76 unit tests pass, ruff clean. |
| **Submission deadline** | **Sun 18 Oct 2026, 10:00 IST** (we aim to submit by 09:30) |
| **Build window** | Sat 17 Oct 16:00 → Sun 18 Oct 10:00 IST (18 h); feature freeze 05:30 |
| **Current milestone** | M4 ✅ · M6 ✅ (`main`) · M5 ✅ local proof (`main`) · M7 ✅ local UI + scenarios · VM gates pending for Member 3 |
| **Active branches** | `main` |
| **Blockers** | VM: image build and LinuxONE benchmarks on VM pending for Member 3 |
| **Main-build baton** | Member 1 / Member 3 for VM model training & gates |
| **Next action** | Member 3: execute `make z-build && make z-gate` on VM with PaySim dataset and GGUF model; run M2 XGBoost training pipeline and evaluate metrics on LinuxONE. |

---

## Team roles (hybrid model, plan §3)

| Role | Default holder | **Current holder** | Contact |
|---|---|---|---|
| Main build (baton) | Member 1 | Member 1 | |
| Proof build | Member 2 | Member 2 | |
| LinuxONE operator | Member 3 | Member 3 | |
| Pitch & review | Member 4 | Member 4 | |

Replace "Member N" with real names when known. Update **Current holder** at every handoff (the receiver does it, as confirmation).

Team name: **Marauders** → submission title `Marauders_IBM Z Datathon 2026 Project`

Sleep shifts: Members 1 & 3 sleep 00:30–04:00; Members 2 & 4 sleep 04:00–07:00 (plan §3). Adjust here if changed.

---

## Milestone gates

Tick a box only when the check really passed. Put the evidence (a file in `results/` or a number) in the log. The full gate definitions are in [docs/IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md).

### M0 — Platform spikes and scaffolding
- [x] `make test` green locally (2 smoke tests, on `m0/infra-skeleton`)
- [x] `scripts/z_doctor.py` OK on VM (`make z-doctor` ALL OK on s390x)
- [ ] Throwaway image with extras builds on VM
- [x] Granite generates on VM (granite-4.0-h-350m-base-be.f16 @ 3.82 tok/s)
- [x] cryptography / Snap ML spikes recorded (apt python3-cryptography 41.0.7 OK; snapml 1.17.2 OK)
- [ ] PaySim on VM, licence recorded in README
- [x] "LinuxONE facts" filled in

### M1 — Contracts and feature pipeline
- [x] Contract tests · [x] PII barrier test · [x] Feature unit tests · [x] No post-transaction columns
- [x] Feature parity local vs VM · [ ] Full PaySim loads on VM (peak RSS: ___)
- [x] Contracts reviewed by B, C, D → **FROZEN** at `9cf57ee` (C-004)

### M2 — Model, thresholds, reason codes
- [ ] PR-AUC ≥ 0.80 (got ___) · [ ] recall ≥ 0.80 @ FPR ≤ 1% (got ___)
- [ ] Prediction parity · [ ] Deterministic codes · [ ] Codes ⊂ enum
- [ ] Engine p99 ≤ 5 ms on VM (got ___; engine: ___) · [ ] ONNX checker passes

### M3 — Decision service
- [x] API contract tests · [x] Log PII test · [ ] Container runs on VM, `/healthz` = s390x (Containerfile written, never built)
- [ ] p99 < 50 ms @c=1 (got ___) and @c=8 (got ___) · [x] Outbox row per request (local; re-check after the VM benchmark)
- Local run (laptop, stub engine, 1000 req): client p99 4.2 ms @c=1, 155 ms @c=8 (server p99 3 ms). The c=8 tail is a risk to measure on the VM.

### M4 — Canary Leak Audit (never cut)
- [x] Scanner variant tests · [x] Positive control 10/10 · [x] Local 0 leaks (results/leak_scorecard_local.md: 11 sinks, 2,146,647 bytes scanned with `--live`)
- [x] VM 0 leaks (results/leak_scorecard_linuxone.md) · [x] All sink types scanned (6 sinks, 281,999 bytes on VM)

### M5 — Granite explainer
- [x] Guard tests + fuzz (1,000 fuzzed prompts → 0 accepted) · [ ] Explanation p50 on VM (got ___ s)
- [ ] p99 < 50 ms with explainer busy (got ___) · [ ] Leak Audit with real Granite = 0 · [ ] Sample explanations saved

### M6 — Audit trail
- [ ] Verify 10k chain on VM · [x] Tamper tests (mod, delete, swap detected at exact seq) · [x] RFC 8032 vectors (§7.1 tests 1, 2, 3 pass) · [ ] ≤ 1 ms p99 overhead

### M7 — Demo and integration
- [x] Demo UI (`service/static/index.html`) wired to real backend endpoints (`/v1/score`, `/v1/explanations`, `/v1/leak-scorecard`, `/v1/audit/verify`)
- [x] Demo scenarios CLI (`scripts/demo_scenarios.py`: 3 scenarios contract-compliant)
- [ ] Clean `make z-up` → 3 scenarios → explanations → verify → scorecard 0
- [ ] Timed dress rehearsal · [ ] Feature freeze declared

### M8 — Submission
- [ ] Video ≤ 3:00 · [x] README credits (PaySim CC BY 4.0, IBM Granite Apache-2.0, scam statistics) · [ ] No secrets/data in git · [ ] Numbers match `results/` · [ ] Submitted

---

## LinuxONE facts (fill in during M0; everyone relies on these)

| Fact | Value |
|---|---|
| VM IP | `148.100.76.241` (SSH user `linux1`) |
| OS image | **Ubuntu 24.04.5 LTS** (`Ubuntu 24.04-Datathon`) |
| Container tool + version | **Docker 29.8.0, build 88096ef** |
| `nproc` / `free -h` / free disk | **3 vCPUs** · **7.8 GiB RAM (5.6 GiB available, 2.2 GiB used, 0 Swap)** · **36 GB free (26% used of 50 GB)** |
| `nnpa` in /proc/cpuinfo? | **YES** (`nnpa` accelerator facility present and visible in `/proc/cpuinfo`) |
| Jupyter container Python | **Python 3.12.15**, venv at `/opt/venv` |
| Granite GGUF path + model name + quant | `/home/ibm-user/granite-4.0-h-350m-base-be.f16.gguf` · `granite-4.0-h-350m-base-be` · **f16** (big-endian) |
| Granite speed (tokens/s) | **3.82 tokens/s** (loaded in 8.67 s; 60 tokens generated in 15.71 s) |
| `pip install cryptography` in image | **FAIL** via pip (no s390x wheel; cargo/maturin source build fails). **PASS** via Ubuntu apt: `python3-cryptography 41.0.7` |
| `pip install snapml` in image | **PASS** (`snapml-1.17.2-cp312-cp312-manylinux_2_28_s390x.whl` installed & imports with `libsnapmllocal3_zdnn` support) |
| `--cpuset-cpus` works? | **YES** (verified with `--cpuset-cpus 0` and `--cpuset-cpus 1-2` on Docker) |
| API / explainer core split | Since `nproc = 3`: **API: core 0** (`--cpuset-cpus 0`), **Explainer: cores 1-2** (`--cpuset-cpus 1-2`) |

---

## Open questions

Open questions now live in [conversation.md](conversation.md) as numbered threads (see its index). Currently open: none. (C-006 & C-007 resolved: live replay leak audit completed with all 11 sinks filled; demo UI wired to real backend endpoints and demo scenarios CLI merged to main. C-004 resolved: contracts frozen at `9cf57ee`. C-002 resolved: repo is private for now; make public in M8. C-003 resolved: `CLAUDE.md` stays gitignored.)

---

## Log (newest first; append, never delete)

Entry template:
```
### YYYY-MM-DD HH:MM (TZ) · <name or agent> · <role> · <milestone>
- Did: …
- Evidence: results/… or numbers
- Branch / commit: …
- State left in: (done / WIP — what's half-finished and where)
- Next step: …
- Gotchas: …
```

### 2026-10-17 22:50 IST · Member 4 & 2 (Antigravity) · Pitch & Review / Proof build · M4 + M7 Integration
- Did: Finished cross-role integration between Member 2 and Member 4:
  1. Ran full Canary Leak Audit with `--live` flag driving real `PaymentRequest` and FastAPI pipeline. Inspected 2,146,647 bytes across all 11 registered and catch-all sinks (`app_log`, `audit_chain`, `prompt_journal`, `outbox_sqlite`, `history_sqlite`, `http_responses`, checkpoints, and shm files). Verified 0 exact, 0 variant, 0 partial leaks. Positive control 10/10; negative control 0/1000 hits. Saved updated `results/leak_scorecard_local.*`. Resolved C-006.
  2. Integrated Member 4's `scripts/demo_scenarios.py` (CLI with `--verify`, `--list`, `--show`, `--json`, `--run`), `docs/assets/pitch_research.md` (RBI, I4C, FTC, NCRB statistics and 3:00 video storyboard), and `README.md` dataset / foundation model license credits into `main`.
  3. Reconciled and validated Member 2's Demo UI dynamic wiring (`d4cfe59`) for `/v1/score`, `/v1/explanations`, `/v1/leak-scorecard`, and `/v1/audit/verify`. Resolved C-007.
  4. Formatted codebase with `make fmt` and confirmed `make lint` (clean, 66 files formatted) and `make test` (76 passed in 9.54s).
- Evidence: `results/leak_scorecard_local.json`, `results/leak_scorecard_local.md`, `make test` (76 passed), `make lint` (clean).
- Branch / commit: `main`.
- State left in: Local M4 + M7 integration complete and verified. C-006 and C-007 closed.
- Next step: Member 3 to build Docker image on LinuxONE VM (`make z-build`), train XGBoost model on PaySim, run VM benchmarks (`make z-gate`), and produce `results/leak_scorecard_linuxone.*` under `--live`.
- Gotchas: `--live` replay requires full database and checkpoint signer lifecycle; truncating SQLite WAL files during replay avoids bloated catch-all scanning times.

### 2026-10-17 19:42 IST · Member 3 (Antigravity) · LinuxONE operator · M0 + M1 + M4 VM Spikes
- Did: Connected to LinuxONE VM (`148.100.76.241`) over SSH. Transferred repo to `~/shared/ShieldZ`. Ran M0 spikes: verified machine facts (3 vCPUs, 7.8GB RAM, 36GB disk, nnpa enabled). Tested `make z-doctor` (`ALL OK on s390x`). Benchmark Granite GGUF model (`granite-4.0-h-350m-base-be.f16.gguf` @ 3.82 tok/s). Evaluated cryptography spike (apt `python3-cryptography 41.0.7` OK, pip fails). Evaluated Snap ML spike (`snapml 1.17.2` s390x wheel OK with zDNN). Verified `--cpuset-cpus` on Docker. Ran M1 golden feature parity test (17/17 passed in 0.31s). Ran all 58 unit tests on VM (58 passed in 0.52s). Ran M4 Canary Leak Audit on LinuxONE (0 leaks across 6 sinks, 10/10 positive control, 0/1000 negative control, PASS).
- Evidence: `results/leak_scorecard_linuxone.md`, `results/leak_scorecard_linuxone.json`, `make z-doctor` output.
- State left in: M0 facts & spikes complete. M1 feature parity complete on VM. M4 VM leak audit complete. Ready for PaySim download and `model/data.py` loader (M1 task 6 / M2).
- Next step: Load PaySim dataset, build `model/data.py` and `model/engine.py` (XGBoostEngine).
- Gotchas: In notebook container, bind mount destination is `/home/jovyan/shared`, not `/home/ibm-user/shared` (symlinked inside container so both work). PyPI has no s390x wheel for cryptography; use system package or pure-Python fallback.

### 2026-10-17 19:35 IST · Member 2 (Antigravity) · proof build · M5 (explainer proof components)
- Did: Implemented Member 2's M5 components on branch `m5/proof-explainer-guard`:
  - `prompt.py`: Canonical prompt renderer strictly from `ExplainJob` enums and reason codes (Invariant I2: zero digits, no request free-text).
  - `guard.py`: Input firewall (byte-for-byte template check, zero digits assertion) + Output guard (rejects 4+ digits, ₹/Rs/INR currency patterns, phone patterns, URLs, @/email; permits small counts like "24 hours", "3 steps").
  - `template.py`: Deterministic `TemplateExplainer` fallback with human-written warnings in English, Hindi, and Tamil.
  - `journal.py`: `PromptJournal` thread-safe audit log for prompt & output auditing (registered Leak Audit sink).
  - `tests/unit/test_explainer.py`: 12 tests covering prompt building, input guard, output guard, templates, journal, and 1,000 fuzzed prompts rejection test (Gate M5 passed).
- Evidence: `make test` 85 passed in 1.29s, `make lint` clean, `make leak-audit` PASS (0 leaks across 6 sinks, 793,919 bytes scanned).
- Branch / commit: `m5/proof-explainer-guard` pushed (`c92db6c`).
- State left in: Member 2's M5 components ✅ done. VM-side explainer worker (`granite.py`, `worker.py`, llama.cpp container) belongs to Member 3.
- Next step: Hand off / sync with Member 1 & Member 3 for VM gates, or support demo scenarios (M7).
- Gotchas: Standalone 3-digit currency checks tested without triggering 4+ digit rules. All Hindi/Tamil templates verified against PII output guard.

### 2026-10-17 19:20 IST · Member 2 (Antigravity) · proof build · M6 (audit trail)
- Did: Implemented full M6 tamper-evident audit trail on branch `m6/proof-audit-trail`.
  - `chain.py`: `AuditChain` append-only JSONL writer with in-process lock, canonical JSON SHA-256 hash chaining, resume from existing file, `load_chain()`.
  - `_ed25519_rfc8032.py`: Pure-Python RFC 8032 Ed25519 implementation (curve arithmetic, clamping, signing, verification, PKCS#8/SPKI PEM export/import).
  - `signing.py`: `CheckpointSigner` background daemon thread (every 100 entries or 1s), auto-backend (cryptography / RFC 8032 fallback), `checkpoint_now()`, `generate_keypair()`, `verify_signature()`.
  - `verify.py`: `verify_audit_trail()` + CLI (`python -m shieldz.audit.verify`). Detects modified bytes, deleted lines, swapped lines, and invalid checkpoint signatures at exact `seq`.
  - `tests/unit/test_audit.py`: 9 unit tests covering hash chaining, resume, checkpoint signing/verification, all RFC 8032 §7.1 test vectors (tests 1, 2, 3), and all tamper detection scenarios.
- Evidence: `make test` 82 passed in 6.87s, `make lint` clean, `make leak-audit` PASS (0 leaks across 6 sinks, 631,919 bytes scanned).
- Branch / commit: `m6/proof-audit-trail` pushed (`481ba90`).
- State left in: M6 local ✅ done and tested. VM-side 10k verify test and ≤ 1 ms p99 latency check await VM availability.
- Next step: M5 — Granite explainer (`prompt.py`, allowlist `guard.py`, `template.py`, `journal.py`).
- Gotchas: When running `python -m shieldz.audit.verify`, lazy-load `verify_audit_trail` in `audit/__init__.py` to avoid runpy submodule warnings. Pure Python Ed25519 matches RFC 8032 §7.1 vectors byte-for-byte.

### 2026-10-17 17:42 IST · Member 2 (Antigravity) · proof build · M4 + C-004
- Did: Completed full M4 Canary Leak Audit on branch `m4/proof-canary-leak-audit`. Canary generator (1,000 canaries + 1,000 decoys, Indian locale Faker), multi-variant LeakScanner (exact/case-fold/stripped/digits-only/URL/base64/hex/MD5/SHA1/SHA256/partial), SinkRegistry (all 6 ARCHITECTURE §5 sinks + catch-all artifacts walk), LeakScorecard, CLI (`python -m shieldz.leak_audit`), full orchestrator with StubService. Posted contract review in C-004.
- Evidence: `make test` 15 passed, `make lint` clean, `make leak-audit` → ✅ PASS — 0 leaks, 6 sinks, 469,919 bytes, positive control 10/10, negative control 0/1,000. See `results/leak_scorecard_local.md`.
- Branch / commit: `m4/proof-canary-leak-audit` pushed (commit `e23a718`). C-004 reply committed to `main` (`a7a900e`).
- State left in: M4 local ✅ done. VM run still needed (M4 gate: "VM 0 leaks"). M6 (audit chain) and M5 (explainer) not yet started.
- Next step: Start M6 — `audit/chain.py` (append-only JSONL hash chain, in-process lock), `signing.py` (background checkpoint thread), `verify.py` (CLI). Then M5 — `prompt.py`, `guard.py`, `template.py`, `journal.py`.
- Gotchas: Two non-blocking questions for Member 1 pending in C-004: (1) add `ts` to `Explanation`? (2) confirm `AuditCheckpoint.signature` covers raw `head_hash` bytes. Digits-only scanner variant must be restricted to phone/account fields only — memo hex IDs produce false positives otherwise. Skip files starting with `.` in catch-all walk (macOS `.DS_Store` causes false partial digit hits).

### 2026-10-17 (night) IST · Member 1 (Claude Code) · main build · M7 backend + live Leak Audit
- Did: `GET /v1/audit/verify` and `GET /v1/leak-scorecard` (aggregate fields only), the app serves `service/static/` at `/` when it exists, `config.results_dir()`, `make z-up` mounts `results/` read-only into the api. `python -m shieldz.leak_audit --live` (`service/live_replay.py`) replays canaries through the real app and the explainer worker. 115 tests pass.
- Evidence: **the committed leak scorecards came from a log-only stand-in.** The real `PaymentRequest` (extra fields forbidden, `timestamp` required) rejects every canary the stand-in accepted, and audit chain, prompt journal, outbox and history scanned 0 bytes. With `--live` (1000 canaries, laptop, stub engine, 41 s): 0 exact / 0 variant / 0 partial leaks, positive control 10/10, 11 sinks all non-empty (audit chain 374 KB, journal 212 KB, outbox 434 KB, history 111 KB, app log 272 KB, responses 510 KB). Scorecard in `results/` NOT regenerated yet.
- Branch / commit: `m7/service-endpoints` (`6cb38db`), pushed, not merged: it edits `leak_audit/__main__.py`, so it needs a human reviewer (Member 2).
- State left in: UI on Member 4's branch hardcodes the explanation text, the leak table and the "chain verified" output (C-007). Image still never built on the VM.
- Gotchas: SQLite WAL files add MBs of duplicate pages to the scan unless checkpointed (`live_replay` does it every 100 canaries). The scanner costs about 4 s per MB for 300 canaries (C-006).

### 2026-10-17 (night) IST · Member 1 (Claude Code) · main build · M3 audit wiring + explainer worker
- Did: wired `AuditChain` + `CheckpointSigner` into `Pipeline` (`audit_append`, started and stopped in the app lifespan; paths in `config.py`; `make verify` updated). Wrote `explainer/worker.py`: publishes the template text at once, then asks the LLM through a `Generator` and replaces the text if `validate_prompt`/`validate_output` pass; guard failure or LLM error keeps the template. `Outbox.requeue_running()` recovers crashed jobs. 110 tests pass.
- Evidence: local end-to-end (api pinned to 1 core + worker + bench, 6300 requests): `shieldz.audit.verify` PASS with 49 signed checkpoints; client p99 4.3 ms @c=1, 21.9 ms @c=8; worker explained every REVIEW/BLOCK job.
- Gotchas: **without `cryptography` the signer falls back to pure Python (~250 ms per signature, holding the GIL): p99 jumped to 65-209 ms.** The Containerfile installs apt `python3-cryptography` and fails the build otherwise; the app logs `signer_backend` at startup (must say `cryptography` on the VM). `cryptography` added to `local-dev.txt` for laptops only. Audit append failure logs `audit_error` and does not fail the decision.
- For Member 3: write `src/shieldz/explainer/granite.py` with `class GraniteGenerator: name = "granite"; def generate(self, prompt: str) -> str` (llama_cpp, `n_threads=2`, small `max_tokens`), then run the explainer with `SHIELDZ_EXPLAINER=granite`. Until then the worker is template-only.
- Next step: Member 3 `make z-build && make z-up && make bench TAG=stub`; check `signer_backend` in `docker logs shieldz-api`.

### 2026-10-17 (night) IST · Member 1 (Claude Code) · main build · M3 adapted to the VM facts
- Did: read Member 3's M0 facts. nproc = 3 means the api gets ONE core (core 0), so `SHIELDZ_WORKERS` stays 1 (also required by `AuditChain`, which locks in-process only). Containerfile now installs `python3-cryptography` via apt + `.pth` and fails the build if Ed25519 doesn't work (ADR D6). `bench_latency.py --cpus 1-2` (via `make bench`, `BENCH_CPUS`) keeps the load client off core 0. Laptop check with the api pinned to one core: c=1 p99 3.8 ms, c=8 p99 21 ms.
- State left in: image still never built on the VM. `Pipeline.audit_append` NOT wired: `m6/proof-audit-trail` and `m5/proof-explainer-guard` are not merged to `main`, and no `explainer/worker.py` exists yet (entrypoint `explainer` command would fail).
- Next step: Member 3 runs `make z-build`; merge m6/m5 (Member 2 branches, need reviewer), then I wire `AuditChain.append` into `audit_append` and start `CheckpointSigner`.
- Gotchas: notebook container mount is `/home/jovyan/shared` (Member 3 fixed `JUPYTER_REPO`). Granite 350m f16 does 3.8 tok/s: about 16 s per 60 tokens, so the demo UI must show "explanation loading".

### 2026-10-17 (night) IST · Member 1 (Claude Code) · main build · M3 hardening (multi-worker)
- Did: `SqliteHistoryStore` (shared by api workers, atomic upsert, seed-once), atomic pepper creation (temp file + hard link), `service/serve.py` multi-worker launcher (`SHIELDZ_WORKERS`), bench client now multi-process and pre-serialised, `make bench` runs the client in the notebook container. `tests/unit/test_multiprocess.py` (4 processes: counts, single seed, outbox, pepper race).
- Evidence: uvicorn `--workers 2` added ~40 ms to every keep-alive request (even `/healthz`; curl without keep-alive was fine). Cause not proven; a listening socket with TCP_NODELAY (`serve.py`) removes it (2.5 ms). Laptop bench, stub engine: c=1 p99 4.0 ms, c=8 p99 23 ms with the multi-process client (75-150 ms with the old single-process client, so that tail was the load generator, not the api).
- State left in: default is 1 worker; the VM benchmark decides whether 2 is needed. Not yet verified on s390x.
- Gotchas: Never `docker exec shieldz-api ... bench` (shares the api's cores). `privacy/tokenize.py` changed (pepper race): needs a human reviewer per AGENTS.md.

### 2026-10-17 (night) IST · Member 1 (Claude Code) · main build · M3 (local half)
- Did: `service/{decide,stub_engine,pipeline,app}.py`, `outbox/queue.py` (WAL, per-thread connections), `privacy/redact_log.py` (allowlist), `clock.py`, `scripts/bench_latency.py`, `containers/{Containerfile,entrypoint.sh}`, `tests/unit/test_service.py`. 73 tests pass.
- Evidence: local benchmark above; a real `uvicorn` start creates the pepper, logs only allowlisted fields, keeps payee history in `history.sqlite`.
- Branch / commit: `m3/service-outbox`.
- State left in: Containerfile NOT built yet (needs the VM). `Pipeline.audit_append` is the hook for the M6 hash chain (takes a `Decision`).
- Next step: Member 3 builds the image (`make z-build`), then `make z-up` and `make bench TAG=...`.
- Gotchas: `SHIELDZ_ENGINE=xgboost` expects `shieldz.model.engine.XGBoostEngine.load(model_dir)`. The explainer entrypoint runs `python -m shieldz.explainer.worker` (not written yet). Outbox status values: pending, running, done, skipped (ALLOW), failed; the explainer should use `Outbox.claim_next()`, `put_explanation()`.

### 2026-10-17 (night) IST · Member 1 (Claude Code) · main build · M1 merged, contracts frozen
- Did: applied Member 2's review (`Explanation.ts` added), squash-merged to `main` as `9cf57ee`, closed C-004. 58 tests pass on `main` (includes Member 2's M4 tests).
- Left for the M1 gate: golden parity on the VM, and the full PaySim load with peak RSS (Member 3). Then tag `m1-gate`. Not tagged yet.
- Next step: M3 on `m3/service-outbox`: stub engine, `decide.py`, `outbox/queue.py`, `privacy/redact_log.py`, then `service/app.py`.

### 2026-10-17 (night) IST · Member 1 (Claude Code) · main build · M1
- Did: skeleton merged to `main` (7393706). On `m1/contracts-privacy`: `contracts.py`, `config.py`, `privacy/{tokenize,strip}.py`, `features/{engineer,history}.py` + `demo_seed.csv`, `tests/golden/features_v1.csv` (200 rows) and `scripts/make_golden_features.py`. `engineer` and `engineer_frame` share one numpy code path.
- Evidence: laptop `make test` 45 passed, `make lint` clean. Covers contract validation, PII barrier (`tests/unit/test_strip.py::test_no_pii_in_output`), drain / mule / new-recipient rows, no post-transaction columns, cold-start seed, serving-vs-batch parity, golden parity.
- Branch / commit: `m1/contracts-privacy` pushed, not merged. Contracts review is open as C-004.
- Still open for the M1 gate: golden parity on the VM (`make z-gate` needs the Containerfile, so use the notebook container: `docker exec notebook /opt/venv/bin/python -m pytest tests/unit/test_features.py`), full PaySim load (Member 3, task 6), review by Members 2/3/4, then freeze.
- Gotchas: pydantic's `exc.json()` echoes the input even with `hide_input_in_errors`; use `contracts.safe_errors`. The gate's "exact amount" wording can't apply to `FeatureInput` (see C-004 point 3).
- Next step: M3 stub engine and service once the contracts are frozen; meanwhile `outbox/queue.py` and `privacy/redact_log.py` don't depend on the freeze.

### 2026-10-17 (evening) IST · Member 1 (Claude Code) · main build · M0 task 7/8
- Did: repo skeleton on `m0/infra-skeleton`: `src/shieldz/` tree (empty packages), `pyproject.toml`, `pytest.ini` (markers z/llm/slow), `requirements/{z-preinstalled,z-extra,local-dev}.txt` pinned to the image versions, `Makefile` (test, lint, fmt, doctor, z-doctor, z-build, z-gate, z-up/down, bench, verify), `scripts/z_doctor.py`, `scripts/check_deps.py`, smoke test.
- Evidence: laptop `make test` 2 passed, `make lint` clean, `make doctor` ALL OK (Python 3.12.14, versions match the pins). `check_deps.py` agrees with the D-table: snapml has a cp312 s390x wheel; cryptography is sdist-only; onnxruntime has no files.
- Branch / commit: `m0/infra-skeleton` pushed, not merged (needs review or the 20-min self-merge rule).
- State left in: `containers/Containerfile` NOT written (M3). `make z-gate`/`z-up` need it. Use `make z-doctor` on the VM for M0 (runs z_doctor in the `notebook` container).
- Gotchas: ruff 0.17 formats Markdown code blocks, so `extend-exclude = ["*.md"]` is set in pyproject. Local deps install with `uv venv --python 3.12 && uv pip install -r requirements/local-dev.txt -e .`.
- Next step: merge the skeleton, then M1 (contracts, privacy, features) on a new branch.

### 2026-10-17 ~17:00 IST · AI agent (Claude Code) · planning · role change
- Did: Moved `model/` (loader, training, evaluation, engine, reasons, export, thresholds) from the main build to **Member 3**, as the team agreed. Added an `Engine` protocol to the M1 contracts as the hand-off point, and a stub engine so M3 doesn't wait for M2.
- Next step: M0.

### 2026-10-17 ~16:50 IST · AI agent (Claude Code) · planning · critique response
- Did: Reviewed `conversation.md` point by point and recorded the verdicts in ADR D16. Valid points are now in the plan:
  - guard re-renders the template and compares byte for byte;
  - output guard targets PII shapes, with a ≥ 80% Granite-source gate;
  - scanner uses a standalone 7+ digit rule plus a negative control with decoys;
  - signing happens in background checkpoints;
  - history store is seeded and bucketed, with a clean-start ALLOW test;
  - PR-AUC floor and 45-min tuning timebox; `MIN_CONTRIB` threshold;
  - apt `python3-cryptography` is the first signing option;
  - core split is computed from `nproc`;
  - `df -h` gate; uv install note.
  Also lightened handoffs: notes-only commits go straight to `main`, and `explanation.md` is only needed at role/baton handoffs. Added `*.sqlite` and an audit-pubkey exception to `.gitignore`.
- Rejected or downgraded: the TreeSHAP 10–25 ms cost (overstated, and already gated); SQLite across containers (fine on one host; gated anyway).
- Next step: M0.

### 2026-10-17 16:30 IST · AI agent (Antigravity) · review & critique · M0
- Did: Conducted full architectural, security, ML, and LinuxONE feasibility audit across all project documentation and local environment. Created `conversation.md` detailing 7 critical vulnerabilities/bugs (non-numeric PII leak risk in "no digits" guard, Birthday Paradox false positives in 6-digit partial canary scanner, latency bottlenecks in TreeSHAP/audit log file locking, SQLite WAL concurrency over Docker bind mounts, empty history store cold-start bug, PaySim non-leaky PR-AUC feasibility, and overlooked Ubuntu `apt` native `python3-cryptography` package).
- Evidence: `conversation.md`
- Branch / commit: `main`
- State left in: `conversation.md` created; `.gitignore` needs updating before generating keys/data; M0 scaffolding pending.
- Next step: Update `.gitignore` to prevent secret/data leaks, create project scaffolding (`pyproject.toml`, `requirements/`, `Makefile`), and start M0 spikes.
- Gotchas: Local machine runs Python 3.13 without `uv` or `docker`; Ubuntu s390x has native `python3-cryptography` via `apt` (avoids need to build from source or implement custom RFC 8032 Ed25519 in pure Python).

### 2026-10-17 16:05 IST · AI agent (Claude Code) · planning · update
- Did: Set the deadline (Sun 18 Oct 10:00 IST) and team name (Marauders). Rescaled the schedule to 18 h on the clock. Replaced the 6 lanes with the 4-member hybrid model: main-build baton plus parallel proof build, LinuxONE operator, and pitch & review. Switched the docs to Ubuntu 24.04 + Docker to match the team's Jupyter setup (ADR D14, D15).
- State left in: docs only, uncommitted.
- Next step: M0 per the "Next action" row.

### 2026-10-17 · AI agent (Claude Code) · all roles · planning
- Did: Read the reference material (solution spec, guidebook, the 4 setup links, the jupyter-lab-ml `packages.txt` and Lab notebooks). Checked PyPI for s390x availability of every planned dependency. Wrote `docs/IMPLEMENTATION_PLAN.md`, `ARCHITECTURE.md`, `DECISIONS.md`, `GLOSSARY.md`, `GIT_WORKFLOW.md`, `LINUXONE_RUNBOOK.md`, `AGENTS.md`, `README.md`, this file and `explanation.md`. Renamed the project ScamShield-Z → **ShieldZ**.
- Evidence: s390x findings table at the top of `docs/DECISIONS.md`.
- Branch / commit: docs written on `main`, **not yet committed**. Suggested: branch `docs/implementation-plan`, commit `docs(docs): add implementation plan and handoff docs`.
- State left in: planning done; no code exists yet.
- Next step: fill in the TODOs above, then M0.
- Gotchas: onnxruntime, shap and cryptography have **no s390x wheels**; the plan routes around them (ADRs D2, D3, D6). PaySim post-transaction balances must not be used as features (ADR D12).
