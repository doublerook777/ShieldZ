# ShieldZ — Progress

> **Read this first** if you are picking up work (human or AI agent). Then read the latest entries in [explanation.md](explanation.md).
> **Update this before you stop**, even mid-task (protocol in [AGENTS.md](AGENTS.md)). `main` must always have a current copy.

---

## Status snapshot (overwrite this block on every update)

| | |
|---|---|
| **Last updated** | 2026-10-17 · planning session (AI agent, Claude Code) |
| **Submission deadline** | **Sun 18 Oct 2026, 10:00 IST** (we aim to submit by 09:30) |
| **Build window** | Sat 17 Oct 16:00 → Sun 18 Oct 10:00 IST (18 h); feature freeze 05:30 |
| **Current milestone** | M0 — not started |
| **Active branches** | none (all work so far is docs on `main`, uncommitted) |
| **Blockers** | none |
| **Main-build baton** | Member 1 · branch: — |
| **Next action** | All members: M0 tasks 1–8 in [docs/IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md#m0--platform-spikes-and-scaffolding-1600--1730--all-members). Member 3: VM facts + spikes · Member 1: repo skeleton · Member 2: PaySim download + licence · Member 4: pitch statistics |

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

- [ ] Is the GitHub repo public, or does the VM need a deploy key?
- [ ] Should `CLAUDE.md` stay gitignored? (`AGENTS.md` carries the shared agent rules either way.)

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
