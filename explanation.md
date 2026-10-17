# ShieldZ — Plain-Language Explanations

**Who reads this:** a teammate who is about to continue someone else's work, possibly with their own AI agent. They need to understand *what was done and why* in a few minutes, without reading the code.

**Who writes this:** every member or AI agent, **before they stop working or run out of context**. Add a new section at the top (newest first). Don't edit other people's sections, except to fix a factual error (and note that you did).

How it differs from [progress.md](progress.md) and [conversation.md](conversation.md): `progress.md` is the status board (checkboxes, numbers, next action). `conversation.md` is where you ask questions or raise critiques that need an answer. This file is the *story* of what you did, in simple words.

---

## How to write an entry

Copy the template below. Rules:
- Write for a smart first-year student who missed the meeting. **No unexplained jargon.** If you must use a term, check that it's in [docs/GLOSSARY.md](docs/GLOSSARY.md) or add it there.
- Keep it short: 10–30 lines is ideal.
- Say what **doesn't** work yet, and what confused you. That's the most valuable part for the next person.
- Give the exact command to see your work running.

```markdown
## YYYY-MM-DD HH:MM (TZ) — <your name or "agent for <name>"> — <milestone / role>

**In one sentence:** …

**What I built or changed (simple words):**
- …

**Why it's done this way:**
- …

**How to see it working:**
    <exact command(s)>  →  <what you should see>

**What's not done / known problems:**
- …

**Things that confused me (so they won't confuse you):**
- …

**If I were continuing, I would next:**
1. …

**Files to look at first:** `path/one.py`, `path/two.py`
```

---

## 2026-10-17 23:25 IST — Member 3 (LinuxONE Operator) — M1 & M2 Complete on LinuxONE

**In one sentence:** Downloaded the full PaySim dataset directly from Kaggle onto the LinuxONE VM, trained an XGBoost fraud detector on 6.06 million rows with zero target leakage, proved 0.9944 PR-AUC and 0.9994 recall at 1% FPR on holdout data, exported verified ONNX models, and achieved 2.24 ms p99 in-process decision latency.

**What I built or changed (simple words):**
- **PaySim Kaggle Download**: Wrote `scripts/download_kaggle_paysim.py` to pull `ealaxi/paysim1` (493.5 MB CSV) directly onto the LinuxONE VM using `kagglehub` in 4.1 s and compressed it to `data/paysim1.csv.gz` (194.7 MB).
- **Data Loader (`shieldz.model.data`)**: Implemented low-memory loading with compact dtypes (`uint16`, `float32`, `uint8`). Full 6.36 million rows load in 17.58 s using only 3.9 GB of RAM (well below the 7.8 GB machine limit). Post-transaction balances (`newbalance*`) and `isFlaggedFraud` are strictly excluded from loading.
- **Reason Code Extraction (`shieldz.model.reasons`)**: Built exact TreeSHAP log-odds mapper (`pred_contribs=True`) mapping top positive contributors to closed `ReasonCode` and discrete `Level` enums without any numeric transaction leakage.
- **Engine Protocol (`shieldz.model.engine.XGBoostEngine`)**: Implemented `contracts.Engine` protocol featuring ultra-fast in-process `inplace_predict` scoring.
- **Training Pipeline (`shieldz.model.train`)**: Trained an XGBoost `tree_method='hist'` booster in 20.74 s with `scale_pos_weight` handling the 0.13% fraud class imbalance.
- **Holdout Evaluation (`shieldz.model.evaluate`)**: Evaluated on 103,573 holdout rows (`step > 600`), achieving **0.9944 PR-AUC** (vs 0.039 baseline) and **0.9994 Recall at 1% FPR**. Thresholds selected: `t_review = 0.70`, `t_block = 0.75`.
- **Latency Benchmark (`results/engine_bench.json`)**: Measured 5,000 single-row queries (`score + reasons`): **p50 = 0.438 ms**, **p95 = 0.842 ms**, **p99 = 2.240 ms** (handily beating the ≤ 5.0 ms target).
- **Parity & Property Tests (`tests/unit/test_parity.py`)**: All 126 unit tests pass on LinuxONE s390x. Verified ONNX export (`model.onnx`) with `onnx.checker`.

**Why it's done this way:**
- Parquet C extensions segfault on big-endian `s390x` machines because dictionary page encodings assume little-endian byte orders. Gzipped CSV (`paysim1.csv.gz`) with `pandas.read_csv` is immune to endianness bugs, fast, and 100% portable.
- `inplace_predict` avoids allocating a new `DMatrix` on every single transaction, which is how we achieved sub-millisecond p50 inference on IBM Z.

**How to see it working:**
    On LinuxONE VM:
    `docker exec -w /home/jovyan/shared/ShieldZ notebook /opt/venv/bin/pytest tests/unit/ -v`  →  126 passed
    `cat results/model_metrics.json`  →  PR-AUC: 0.9944, ROC-AUC: 0.9999
    `cat results/engine_bench.json`  →  p99: 2.24 ms

**What's not done / known problems:**
- Docker image `shieldz:latest` (`make z-build`) and live service benchmark on LinuxONE container stack (`make bench TAG=real`).

**If I were continuing, I would next:**
1. Run `make z-build` on the VM to build the container image.
2. Run `make z-up` to bring up `shieldz-api` and `shieldz-explainer`.
3. Run `make bench TAG=real` on the VM to verify end-to-end HTTP p99 < 50 ms.

**Files to look at first:** `src/shieldz/model/data.py`, `src/shieldz/model/train.py`, `src/shieldz/model/engine.py`, `results/model_metrics.json`

---

## 2026-10-17 22:50 IST — Member 4 (Pitch & Review) & Member 2 (Proof build) — M4 + M7 Integration

**In one sentence:** We closed out the local proof and pitch tasks by running the Canary Leak Audit with live service replay across all 11 sinks with 0 leaks, integrated the 3 contract-compliant demo scenarios and pitch research, and resolved C-006 and C-007.

**What I built or changed (simple words):**
- Replayed 1,000 canaries + 1,000 decoys through the real FastAPI service using `--live`. Instead of writing only to an app log stand-in, this exercised `PaymentRequest`, feature stripping, the outbox, the explainer worker, and the audit chain. 2.15 MB across 11 sinks were inspected, 0 leaks were found, and 10/10 positive control canaries were detected.
- Merged Member 4's CLI demo runner (`scripts/demo_scenarios.py`) which defines three realistic scam stories (Digital Arrest, Routine Electricity Bill, Borderline Clinic).
- Added pitch research (`docs/assets/pitch_research.md`) citing RBI, I4C, FTC, and NCRB statistics with a 3-minute video storyboard.
- Confirmed that Member 2's UI wiring dynamically calls `/v1/score`, `/v1/explanations`, `/v1/leak-scorecard`, and `/v1/audit/verify`.
- Formatted the codebase with `make fmt` and confirmed all 76 unit tests pass and `make lint` is clean.

**Why it's done this way:**
- As noted in C-006, running the leak audit against a stand-in left SQLite and journal sinks at 0 bytes. Running `--live` proves that all system sinks stay 100% leak-free even under actual live database writes and JSON-RPC responses.
- The single-page UI is served directly from the FastAPI root `/` and interacts with real endpoints so live demo judges see genuine measurements.

**How to see it working:**
    .venv/bin/python scripts/demo_scenarios.py --verify  →  All scenarios are 100% contract compliant
    .venv/bin/python scripts/demo_scenarios.py --list    →  Lists the 3 scenarios
    make test                                           →  76 passed
    make lint                                           →  All checks passed

**What's not done / known problems:**
- LinuxONE VM image (`make z-build`) and training the XGBoost model on the VM with full PaySim data (Member 3's role) is the remaining milestone task.

**If I were continuing, I would next:**
1. Support Member 3 in running `make z-build` and `make z-gate` on the VM.
2. Record the 3:00 demo video following the storyboard in `docs/assets/pitch_research.md`.

**Files to look at first:** `scripts/demo_scenarios.py`, `docs/assets/pitch_research.md`, `results/leak_scorecard_local.md`

---

## 2026-10-17 16:30 IST — AI agent (Antigravity) — project analysis & critique

**In one sentence:** I did a deep engineering and architectural review of the entire ShieldZ plan, identified 7 critical vulnerabilities and operational risks, and documented them with solutions in `conversation.md`.

**What I built or changed (simple words):**
- Wrote `conversation.md`: a complete technical critique covering the prompt guards, the canary leak scanner, system latency, Docker/SQLite concurrency, machine learning targets on PaySim, and LinuxONE crypto options.
- Updated `progress.md` with the new findings and next steps.

**Why it's done this way:**
- Finding design traps now (at 16:30) saves hours of debugging later when running against the clock.
- For example, Ubuntu 24.04 on LinuxONE already has `python3-cryptography` available via `apt`, meaning we don't need to waste time compiling Rust or writing pure-Python elliptic curve math. Also, the canary scanner's 6-digit partial rule would cause false alarms on timestamps and hashes unless fixed.

**How to see it working:**
    Read `conversation.md` to see the detailed breakdown and priority recommendations.

**What's not done / known problems:**
- Code scaffolding (`Makefile`, `pyproject.toml`, `requirements/`, `contracts.py`) has not been written yet.
- `.gitignore` needs to be updated with `data/` and `artifacts/` before files are created.

**Things that confused me (so they won't confuse you):**
- The prompt guard relies on "no digits" to prevent PII leaks, but personal names contain letters, not digits! We need explicit string entity checks, not just a digit check.
- The 6-digit canary partial check will easily collide with random digits in timestamps or hashes (Birthday Paradox).

**If I were continuing, I would next:**
1. Update `.gitignore` so secrets and data are never accidentally committed.
2. Create the M0 repo skeleton (`pyproject.toml`, `requirements/local-dev.txt`, `Makefile`).
3. Define the shared data contracts in `src/shieldz/contracts.py`.

**Files to look at first:** `conversation.md`, `progress.md`

---

## 2026-10-17 16:05 IST — agent (Claude Code) for the team lead — planning update

**In one sentence:** We have 18 hours (deadline Sun 10:00 IST) and 4 people, so the plan now has clock times and four roles. It also uses Docker, because that's what our VM runs.

**What changed (simple words):**
- **Four roles instead of six lanes.**
  - Member 1 holds the "main build": the chain of steps that each depend on the previous one (data shapes → features → model → web service).
  - Only one person works on the main build at a time. When they sleep or run out of AI tokens, they pass it on like a relay baton.
  - Member 2 builds the privacy proof (Leak Audit, tamper-proof log, prompt safety check) in separate folders.
  - Member 3 runs everything on LinuxONE.
  - Member 4 does the pitch, reviews code and covers the main build at night.
- **Sleep shifts:** Members 1 and 3 sleep 00:30–04:00; Members 2 and 4 sleep 04:00–07:00. Everyone works on the video from 07:00.
- **Docker, not Podman:** the team set up the VM with the Ubuntu + Docker guide, so all commands now use `docker`. This corrects my earlier note below that said Podman.

**How to see it:** read `docs/IMPLEMENTATION_PLAN.md` §3 (roles, handoff steps, sleep table) and the "Team roles" table in `progress.md`.

**If I were continuing, I would next:** start M0. Each member's first task is in the "Next action" row of `progress.md`.

---

## 2026-10-17 — agent (Claude Code) for the team lead — planning, all lanes

**In one sentence:** No code exists yet. I wrote the full plan and the team docs, so everyone can start building in parallel.

**What I built or changed (simple words):**
- A step-by-step plan (`docs/IMPLEMENTATION_PLAN.md`) with nine milestones, M0 to M8. Each milestone ends with a checklist (a "gate") that must pass, first on a laptop and then on our LinuxONE machine, before we move on.
- A description of how the system fits together (`docs/ARCHITECTURE.md`), a list of every technical word in plain language (`docs/GLOSSARY.md`), how we use git (`docs/GIT_WORKFLOW.md`), how to use the LinuxONE machine (`docs/LINUXONE_RUNBOOK.md`) and a record of every design choice (`docs/DECISIONS.md`).
- The project is now called **ShieldZ** (it was ScamShield-Z).

**Why it's done this way:**
- LinuxONE uses a different kind of processor (s390x) from our laptops. Some popular Python libraries don't exist for it, including the ones the original idea relied on (onnxruntime, shap, cryptography). I checked each one and changed the plan to use what's already installed on the LinuxONE image: XGBoost can do the SHAP explanations itself, and Granite runs through llama.cpp, as in Lab 2.
- We write code on laptops because it's faster, but every milestone is checked on LinuxONE, so we never find out at the last minute that something doesn't run there.
- PaySim has columns showing the balance *after* the payment. A real bank wouldn't know those before deciding, so using them would be cheating. We leave them out.

**How to see it working:**
    Nothing to run yet. Start by reading progress.md, then IMPLEMENTATION_PLAN.md §2 (how we work) and §4 M0.

**What's not done / known problems:**
- Not known yet, to be found in M0: the exact Granite model file in the image, whether `cryptography` and `snapml` install on the VM, how much memory and how many CPU cores the VM has.
- The docs aren't committed to git yet.

**Things that confused me (so they won't confuse you):**
- The official Jupyter README talks about Docker, but on the RHEL image it's Podman. The commands are the same; just swap the word.
- `CLAUDE.md` and `reference/` are in `.gitignore`, so the original solution document isn't in the repo. Everything important from it is now in `docs/`.

**If I were continuing, I would next:**
1. Fill in the deadline, the team name and the lane owners in progress.md.
2. Do M0 on the VM: run the "facts" commands from the runbook §2 and find the Granite model.
3. Create the repo skeleton (M0 task 7).

**Files to look at first:** `progress.md`, `docs/IMPLEMENTATION_PLAN.md`, `docs/ARCHITECTURE.md`
