# ShieldZ — Progress

> **Read this first** if you are picking up work (human or AI agent). Then read the latest entries in [explanation.md](explanation.md).
> Questions or critiques for others go in [conversation.md](conversation.md).
> **Update this before you stop**, even mid-task (protocol in [AGENTS.md](AGENTS.md)). `main` must always have a current copy.

---

## Status snapshot (overwrite this block on every update)

| | |
|---|---|
| **Last updated** | 2026-10-17 · contracts frozen, M1 merged to `main` (Member 1, Claude Code) |
| **Submission deadline** | **Sun 18 Oct 2026, 10:00 IST** (we aim to submit by 09:30) |
| **Build window** | Sat 17 Oct 16:00 → Sun 18 Oct 10:00 IST (18 h); feature freeze 05:30 |
| **Current milestone** | M1 gate: remaining items are VM-side (Member 3: golden parity, full PaySim load) · M3 main build next |
| **Active branches** | main |
| **Blockers** | None. Two non-blocking questions for Member 1: (1) `Explanation.ts` field? (2) What bytes does `AuditCheckpoint.signature` cover? (see C-004 reply) |
| **Main-build baton** | Member 1 · branch: — |
| **Next action** | Member 2: start M6 (`audit/chain.py`, `signing.py`, `verify.py`) while waiting for M1 freeze. Member 1: see C-004 for 2 quick questions. Member 3/4: please reply to C-004. |

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
- [ ] `scripts/z_doctor.py` OK on VM
- [ ] Throwaway image with extras builds on VM
- [ ] Granite generates on VM (model + tok/s recorded below)
- [ ] cryptography / Snap ML spikes recorded; ADR D2, D6 updated
- [ ] PaySim on VM, licence recorded in README
- [ ] "LinuxONE facts" filled in

### M1 — Contracts and feature pipeline
- [ ] Contract tests · [ ] PII barrier test · [ ] Feature unit tests · [ ] No post-transaction columns
- [ ] Feature parity local vs VM · [ ] Full PaySim loads on VM (peak RSS: ___)
- [x] Contracts reviewed by B, C, D → **FROZEN** at `9cf57ee` (C-004)

### M2 — Model, thresholds, reason codes
- [ ] PR-AUC ≥ 0.80 (got ___) · [ ] recall ≥ 0.80 @ FPR ≤ 1% (got ___)
- [ ] Prediction parity · [ ] Deterministic codes · [ ] Codes ⊂ enum
- [ ] Engine p99 ≤ 5 ms on VM (got ___; engine: ___) · [ ] ONNX checker passes

### M3 — Decision service
- [ ] API contract tests · [ ] Log PII test · [ ] Container runs on VM, `/healthz` = s390x
- [ ] p99 < 50 ms @c=1 (got ___) and @c=8 (got ___) · [ ] Outbox row per request

### M4 — Canary Leak Audit (never cut)
- [x] Scanner variant tests · [x] Positive control 10/10 · [x] Local 0 leaks (results/leak_scorecard_local.md)
- [ ] VM 0 leaks (scorecard: ___) · [x] All sink types scanned (6 sinks, 469,919 bytes)

### M5 — Granite explainer
- [ ] Guard tests + fuzz · [ ] Explanation p50 on VM (got ___ s)
- [ ] p99 < 50 ms with explainer busy (got ___) · [ ] Leak Audit with real Granite = 0 · [ ] Sample explanations saved

### M6 — Audit trail
- [ ] Verify 10k chain · [ ] Tamper tests · [ ] RFC 8032 vectors (if own impl) · [ ] ≤ 1 ms p99 overhead

### M7 — Demo and integration
- [ ] Clean `make z-up` → 3 scenarios → explanations → verify → scorecard 0
- [ ] Timed dress rehearsal · [ ] Feature freeze declared

### M8 — Submission
- [ ] Video ≤ 3:00 · [ ] README credits · [ ] No secrets/data in git · [ ] Numbers match `results/` · [ ] Submitted

---

## LinuxONE facts (fill in during M0; everyone relies on these)

| Fact | Value |
|---|---|
| VM IP | _TODO (don't commit the SSH key!)_ |
| OS image | **Ubuntu 24.04-Datathon** (confirmed by team, 2026-10-17) |
| Container tool + version | **Docker 29.8.0** (confirmed by team, 2026-10-17) |
| `nproc` / `free -h` / free disk | _TODO_ |
| `nnpa` in /proc/cpuinfo? | _TODO_ |
| Jupyter container Python | _TODO (expected 3.12, /opt/venv)_ |
| Granite GGUF path + model name + quant | _TODO_ |
| Granite speed (tokens/s) | _TODO_ |
| `pip install cryptography` in image | _TODO pass/fail_ |
| `pip install snapml` in image | _TODO pass/fail_ |
| `--cpuset-cpus` works? | _TODO_ |
| API / explainer core split | _TODO_ |

---

## Open questions

Open questions now live in [conversation.md](conversation.md) as numbered threads (see its index). Currently open: none. (C-004 resolved: contracts frozen at `9cf57ee`.) (C-002 resolved: repo is private for now, so the VM uses a deploy key; make it public in M8. C-003 resolved: `CLAUDE.md` stays gitignored.)

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

### 2026-10-17 17:42 IST · Member 2 (Antigravity) · proof build · M4 + C-004
- Did: Completed full M4 Canary Leak Audit on branch `m4/proof-canary-leak-audit`. Canary generator (1,000 canaries + 1,000 decoys, Indian locale Faker), multi-variant LeakScanner (exact/case-fold/stripped/digits-only/URL/base64/hex/MD5/SHA1/SHA256/partial), SinkRegistry (all 6 ARCHITECTURE §5 sinks + catch-all artifacts walk), LeakScorecard, CLI (`python -m shieldz.leak_audit`), full orchestrator with StubService. Posted contract review in C-004.
- Evidence: `make test` 15 passed, `make lint` clean, `make leak-audit` → ✅ PASS — 0 leaks, 6 sinks, 469,919 bytes, positive control 10/10, negative control 0/1,000. See `results/leak_scorecard_local.md`.
- Branch / commit: `m4/proof-canary-leak-audit` pushed (commit `e23a718`). C-004 reply committed to `main` (`a7a900e`).
- State left in: M4 local ✅ done. VM run still needed (M4 gate: "VM 0 leaks"). M6 (audit chain) and M5 (explainer) not yet started.
- Next step: Start M6 — `audit/chain.py` (append-only JSONL hash chain, in-process lock), `signing.py` (background checkpoint thread), `verify.py` (CLI). Then M5 — `prompt.py`, `guard.py`, `template.py`, `journal.py`.
- Gotchas: Two non-blocking questions for Member 1 pending in C-004: (1) add `ts` to `Explanation`? (2) confirm `AuditCheckpoint.signature` covers raw `head_hash` bytes. Digits-only scanner variant must be restricted to phone/account fields only — memo hex IDs produce false positives otherwise. Skip files starting with `.` in catch-all walk (macOS `.DS_Store` causes false partial digit hits).

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
