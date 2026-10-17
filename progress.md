# ShieldZ — Progress

> **Read this first** if you are picking up work (human or AI agent). Then read the latest entries in [explanation.md](explanation.md).
> Questions or critiques for others go in [conversation.md](conversation.md).
> **Update this before you stop**, even mid-task (protocol in [AGENTS.md](AGENTS.md)). `main` must always have a current copy.

---

## Status snapshot (overwrite this block on every update)

| | |
|---|---|
| **Last updated** | 2026-10-17 ~16:50 IST · critique merged into docs (AI agent, Claude Code) |
| **Submission deadline** | **Sun 18 Oct 2026, 10:00 IST** (we aim to submit by 09:30) |
| **Build window** | Sat 17 Oct 16:00 → Sun 18 Oct 10:00 IST (18 h); feature freeze 05:30 |
| **Current milestone** | M0 — not started (critique reviewed and folded into the docs, ADR D16) |
| **Active branches** | main |
| **Blockers** | none |
| **Main-build baton** | Member 1 · branch: — |
| **Next action** | M0 now (we're behind schedule). Member 1: repo skeleton · Member 3: VM facts + spikes (signing: try apt `python3-cryptography` first) · Member 2: PaySim + licence · Member 4: pitch statistics |

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
- [ ] `make test` green locally
- [ ] `scripts/z_doctor.py` OK on VM
- [ ] Throwaway image with extras builds on VM
- [ ] Granite generates on VM (model + tok/s recorded below)
- [ ] cryptography / Snap ML spikes recorded; ADR D2, D6 updated
- [ ] PaySim on VM, licence recorded in README
- [ ] "LinuxONE facts" filled in

### M1 — Contracts and feature pipeline
- [ ] Contract tests · [ ] PII barrier test · [ ] Feature unit tests · [ ] No post-transaction columns
- [ ] Feature parity local vs VM · [ ] Full PaySim loads on VM (peak RSS: ___)
- [ ] Contracts reviewed by B, C, D → **FROZEN**

### M2 — Model, thresholds, reason codes
- [ ] PR-AUC ≥ 0.80 (got ___) · [ ] recall ≥ 0.80 @ FPR ≤ 1% (got ___)
- [ ] Prediction parity · [ ] Deterministic codes · [ ] Codes ⊂ enum
- [ ] Engine p99 ≤ 5 ms on VM (got ___; engine: ___) · [ ] ONNX checker passes

### M3 — Decision service
- [ ] API contract tests · [ ] Log PII test · [ ] Container runs on VM, `/healthz` = s390x
- [ ] p99 < 50 ms @c=1 (got ___) and @c=8 (got ___) · [ ] Outbox row per request

### M4 — Canary Leak Audit (never cut)
- [ ] Scanner variant tests · [ ] Positive control 10/10 · [ ] Local 0 leaks
- [ ] VM 0 leaks (scorecard: ___) · [ ] All sink types scanned

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

Open questions now live in [conversation.md](conversation.md) as numbered threads (see its index). Currently open: **C-002** (repo public or deploy key?), **C-003** (should `CLAUDE.md` stay gitignored?).

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
