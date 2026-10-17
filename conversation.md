# ShieldZ — Team Conversation Board

The place where members and their AI agents **raise critiques, ask questions, propose changes and flag blockers** to each other, asynchronously, across shifts.

| File | Use it for |
|---|---|
| `progress.md` | Status: what's done, what's next, who holds what |
| `explanation.md` | The story of a finished session, in simple words (at handoffs) |
| **`conversation.md`** | **Anything that needs an answer or a decision from someone else** |
| `docs/DECISIONS.md` | The final record of decisions. A thread that changes a decision must end up there |

---

## How to use this board

1. **One thread per topic.** Take the next free ID from the index (`C-004`, `C-005`, …), add a row to the index and put the thread **at the top** of "Threads" (newest first).
2. **Reply inside the thread**, at the bottom of its *Replies* list (oldest first within a thread). Start each reply with `**<Member N or agent for Member N> · HH:MM IST:**`.
3. **Never rewrite someone else's text.** To retract your own, use ~~strikethrough~~ and add a reply.
4. **Status** (keep the index and the thread in sync):
   - 🟡 open: needs an answer
   - 🔵 answered: an answer was given, the action is pending
   - ✅ resolved: done
   - ⛔ won't fix: closed with a reason
5. **Closing a thread:** fill in its **Outcome** with what was decided and *where it was applied* (ADR number, plan section, commit). This board is a discussion, not the source of truth. The docs are.
6. **Blockers:** also put them in the `Blockers` row of the `progress.md` snapshot, and tell the team chat if it's urgent.
7. **Good critiques are specific:** name the file/section, give a concrete failure scenario, propose a fix.
8. **Committing:** this file counts as notes. Commit straight to `main` (`git pull --rebase` first), with a message like `docs(conversation): C-004 open — …`. On a merge conflict, keep both sides.
9. **AI agents:**
   - At session start, read every 🟡/🔵 thread whose *For* field matches your role or member.
   - If you hit a question that is the *team's* call (not something you can settle from the code or docs), open a thread and keep working on something else instead of guessing.
   - Before you stop, reply to any thread you were working on.

### Thread template

```markdown
## C-00N · <short title>
**Type:** critique | question | proposal | blocker | FYI · **Status:** 🟡 open · **Opened by:** <who>, <YYYY-MM-DD HH:MM IST> · **For:** <Member N / role / everyone> · **Related:** <files, plan §, ADR>

<the point, with a concrete scenario and a suggested answer or fix if you have one>

**Replies**
- **<who> · HH:MM IST:** …

**Outcome:** _(when closing: decision + where it was applied)_
```

---

## Index

| ID | Title | Type | For | Status |
|---|---|---|---|---|
| [C-003](#c-003--should-claudemd-stay-gitignored) | Should `CLAUDE.md` stay gitignored? | question | team lead | ✅ resolved |
| [C-002](#c-002--is-the-github-repo-public-or-does-the-vm-need-a-deploy-key) | Is the GitHub repo public, or does the VM need a deploy key? | question | team lead, Member 3 | ✅ resolved |
| [C-001](#c-001--deep-project-analysis-bugs-shortcomings--critique) | Deep project analysis, bugs, shortcomings & critique | critique | everyone | ✅ resolved |

---

# Threads

## C-003 · Should `CLAUDE.md` stay gitignored?
**Type:** question · **Status:** ✅ resolved · **Opened by:** agent (Claude Code), 2026-10-17 17:10 IST · **For:** team lead · **Related:** `.gitignore`, `AGENTS.md`

`CLAUDE.md` and `reference/` are in `.gitignore`, so they never reach teammates' clones. Nothing breaks: `AGENTS.md` (committed) holds every shared agent rule, and the local `CLAUDE.md` just imports it. But members using Claude Code won't get the import unless they create their own `CLAUDE.md` containing `@AGENTS.md`.
Suggested answer: commit a `CLAUDE.md` that only contains `@AGENTS.md`, **or** keep it ignored and tell Claude Code users to create that one-liner.

**Replies**
- **Team lead · 17:20 IST:** Keep `CLAUDE.md` gitignored.

**Outcome:** `CLAUDE.md` stays gitignored. Members using Claude Code create a local `CLAUDE.md` containing just `@AGENTS.md` (instruction added to `AGENTS.md`). All shared rules stay in `AGENTS.md`.

---

## C-002 · Is the GitHub repo public, or does the VM need a deploy key?
**Type:** question · **Status:** ✅ resolved · **Opened by:** agent (Claude Code), 2026-10-17 17:10 IST · **For:** team lead, Member 3 · **Related:** `docs/LINUXONE_RUNBOOK.md` §2

The VM clones the repo into `~/shared/ShieldZ`. A public repo clones over HTTPS with no setup. A private repo needs a read-only deploy key on the VM (steps in runbook §2). The submission needs the repo link to be accessible to judges by 10:00 anyway.

**Replies**
- **Team lead · 17:20 IST:** ~~The repo is public.~~
- **Team lead · 17:30 IST:** Correction: the repo is **private for now** and will be made public later.

**Outcome:** The VM needs a **read-only deploy key** to clone (runbook §2) until the repo goes public. Making the repo public is now an **M8 submission checklist item**, because judges need the link. Treat the repo as public already: the never-commit rules (keys, data, `artifacts/`) are strict.

---

## C-001 · Deep project analysis, bugs, shortcomings & critique
**Type:** critique · **Status:** ✅ resolved · **Opened by:** Lokesh (AI agent, Antigravity), 2026-10-17 16:30 IST · **For:** everyone · **Related:** all docs; ADR D16

**Outcome:** every finding was reviewed. Fixes are in commit `8e58a4d`, and the verdicts are in ADR D16 and the resolution log below (§8).

> **Document purpose:** Critical technical analysis of the ShieldZ project architecture, implementation plan, security/privacy claims, machine learning pipeline, and LinuxONE (s390x) deployment.
> **Date:** October 17, 2026 · IBM Z Datathon 2026 (Theme 2: AI Secured — Innovation Without Exposure)
> **Target Audience:** Team Marauders (Members 1, 2, 3, 4) and collaborating AI agents.
>
> **Status (17:00 IST):** every point below has been reviewed. The fixes are in the docs as of commit `8e58a4d`. See [§8 Resolution log](#8-resolution-log-what-was-fixed-and-where) at the end of this file, and ADR D16 in `docs/DECISIONS.md`.

---

### 1. Executive Summary & Project Status

ShieldZ is an ambitious, well-conceptualized project combining real-time fraud scoring (XGBoost), privacy-preserving explainability (IBM Granite LLM via llama.cpp on LinuxONE), tamper-evident audit logging (hash chaining + Ed25519), and a headline Canary Leak Audit. The planning documents (`docs/ARCHITECTURE.md`, `IMPLEMENTATION_PLAN.md`, `DECISIONS.md`, `monkey_brain.md`) are exceptionally thorough and well-written.

However, a deep engineering audit of the codebase, planning assumptions, and runtime environment reveals **critical vulnerabilities, performance bottlenecks, mathematical edge cases in the leak scanner, and operational roadblocks** that could jeopardize the project during the 18-hour build window.

#### Current Reality Check
- **Clock Time:** Hackathon start was 16:00 IST; current time is past 16:25 IST. Over 25 minutes of the 18-hour sprint have elapsed.
- **Codebase State:** **Zero application code, tests, or scaffolding exist.** No `Makefile`, no `pyproject.toml`, no `requirements/*.txt`, no `Containerfile`, and no `src/` directory. Only documentation has been created.
- **Milestone Status:** Milestone M0 (Platform Spikes & Scaffolding) was scheduled for 16:00–17:30 IST and is currently marked "not started".

---

### 2. Critical Bugs & Architectural Shortcomings

#### 2.1. The "No Digits" Prompt & Output Guard False Sense of Security
* **Reference:** `docs/ARCHITECTURE.md` §4, §6 (Invariant I2); `docs/IMPLEMENTATION_PLAN.md` M5; `explainer/guard.py`.
* **The Claim:** Invariant I2 states: *"The LLM prompt is built only from the template and enum values; no digits."* The prompt guard asserts: *"Does it contain ANY digit (0-9)? must be none!"* And the output guard states: *"Falls back to the template if the LLM output contains digits, URLs or @"*.
* **Critical Flaws:**
  1. **Leaves Non-Numeric PII Completely Exposed:** PII does not only consist of digits. Names (e.g., *"Kamala Devi"*, *"Rukmini Venkataraghavan"*), physical addresses, city names, email local parts, and transaction memo text contain letters, not numbers. If a bug in `privacy.strip()` passes a raw name into downstream components or the prompt builder, the "no digits" rule will **never catch it**.
  2. **The Granite Output Rejection Trap:** IBM Granite is a pre-trained LLM. In natural financial advice, LLMs routinely generate numbers: e.g., *"call your bank within 24 hours"*, *"follow these 3 steps"*, *"available 7 days a week"*, or *"step 1: pause"*. Because the output guard rejects any output containing digits `0-9` and falls back to `TemplateExplainer`, **Granite's generated outputs could be rejected 100% of the time in production**, silently masking the failure by always showing the hardcoded template. The team would effectively be showcasing static templates while claiming Granite is generating the text.
  3. **Brittle Prompt Templating:** The "no digits" rule breaks if prompt instructions contain digits (e.g., "write 2-3 sentences" had to be manually edited to "write two or three sentences"). Any versioning string like `v1` or metadata in prompt debugging will immediately trip the firewall.

#### 2.2. Mathematical Flaw in Canary Scanner: The Birthday Paradox / Pigeonhole Trap
* **Reference:** `docs/ARCHITECTURE.md` §7; `docs/IMPLEMENTATION_PLAN.md` M4; `leak_audit/scanner.py`.
* **The Rule:** `scanner.py` specifies that *"Any 6 or more consecutive digits of a phone or account number counts as a PARTIAL leak."*
* **Critical Flaw:**
  - With 1,000 canaries generated by Faker, each having a 10-digit phone number and a 10-to-12-digit account number, each canary generates approximately 5 to 7 unique 6-digit substrings.
  - Across 1,000 canaries, there are roughly **$10,000$ to $12,000$ distinct 6-digit integer patterns**.
  - There are only $1,000,000$ possible 6-digit sequences ($000000$ to $999999$).
  - System logs, Unix timestamps in milliseconds (`1729163589123`), UUIDs, Docker container IDs, and hash digests contain millions of characters.
  - By the Birthday Paradox, the mathematical probability of a random 6-digit string occurring in legitimate log files, timestamps, or SHA-256 hex hashes and colliding with one of the 12,000 canary substrings approaches **100%**.
  - **Consequence:** The Canary Leak Audit will generate **false positive `PARTIAL` leaks**, making it impossible to pass Gate M4 (`0 leaks, 0 partials`), even when zero PII was leaked.
* **Fix Required:** The scanner must look for exact delimited patterns (e.g., regex `\b\d{10}\b`), or require structured token matches, rather than raw unanchored 6-digit substring scanning across unstructured binary/text files.

#### 2.3. The Synchronous Latency Budget vs. File-Locked Audit & TreeSHAP
* **Reference:** `docs/ARCHITECTURE.md` §1, §3; `docs/IMPLEMENTATION_PLAN.md` M2, M3, M6.
* **The Claim:** The decision path achieves `< 50 ms p99` end-to-end at concurrency $c=8$.
* **The Bottlenecks:**
  1. **TreeSHAP Computation Overhead:** The decision path calls `booster.predict(dmatrix, pred_contribs=True)` synchronously for REVIEW/BLOCK decisions to calculate SHAP feature attributions. While XGBoost's TreeSHAP is fast in C++, running full tree traversal to compute Shapley values on every evaluation adds significant CPU latency (often 10–25 ms per request on CPU), eroding the 50 ms budget.
  2. **Audit Log Lock Contention:** `docs/IMPLEMENTATION_PLAN.md` M6 mandates an append-only `audit/chain.jsonl` with *"a single writer with a file lock"*. Under concurrency $c=8$, eight simultaneous requests will compete for the same OS file lock. Each request must acquire the lock, read the tail hash, compute canonical JSON, compute SHA-256, perform Ed25519 signing, and write. Serializing 8 concurrent threads through an exclusive file lock will introduce queuing delays that will cause p99 latency to spike far beyond 50 ms.
  3. **Pure-Python Ed25519 (ADR D6 Fallback):** If `pip install cryptography` fails (which is probable on s390x without Rust), the plan falls back to pure-Python RFC 8032 Ed25519. In pure Python, signing takes **10–20 ms per signature** on CPU. Doing this synchronously inside an exclusive file lock guarantees failure of the `< 50 ms p99` latency gate.

#### 2.4. Cross-Container SQLite Concurrency on Docker Bind Mounts
* **Reference:** `docs/ARCHITECTURE.md` §2, §5; `docs/DECISIONS.md` ADR D5; `docs/LINUXONE_RUNBOOK.md` §5.
* **The Design:** `shieldz-api` writes explain jobs to `outbox.sqlite`, and `shieldz-explainer` polls `outbox.sqlite`. Both containers mount `~/shared/ShieldZ/artifacts:/app/artifacts`.
* **The Risk:**
  - SQLite WAL mode relies on shared memory (`outbox.sqlite-shm`) and POSIX advisory locking via `mmap`.
  - When two separate Docker containers access the same SQLite database file across host bind mounts, POSIX lock semantics and memory-mapped files can fail or trigger `sqlite3.OperationalError: database is locked`, especially across different process namespaces.
  - Additionally, user permissions on bind mounts frequently cause access denial errors unless the UID inside both containers is identical (e.g. UID 1000 in Jupyter vs UID 0 or 1001 in Docker).

#### 2.5. Cold-Start Problem in History Store (`features/history.py`)
* **Reference:** `docs/ARCHITECTURE.md` §3; `docs/IMPLEMENTATION_PLAN.md` M1.
* **The Signal:** `payee_prior_inbound` (counted chronologically; low = new/rarely used recipient -> `NEW_RECIPIENT` reason code).
* **The Bug:**
  - When the service boots in production or during testing, `history.sqlite` is completely empty.
  - Every single incoming transaction—including legitimate bill payments and familiar recipients—will evaluate to `payee_prior_inbound = 0`.
  - Every payment will therefore trigger the `NEW_RECIPIENT` high-risk signal.
  - In demo scenario (b) (*"normal bill payment -> ALLOW"*), an empty history store could push the score into REVIEW or BLOCK, ruining the live demo.
  - The plan lacks any warm-up/seeding mechanism to populate baseline recipient transaction history before serving requests.

---

### 3. Machine Learning & Dataset Reality Checks

#### 3.1. PaySim Class Imbalance & Metric Feasibility (PR-AUC $\ge$ 0.80)
* **Reference:** `docs/IMPLEMENTATION_PLAN.md` M2 Gate (`PR-AUC >= 0.80`, `recall >= 0.80 at FPR <= 1%`); `docs/DECISIONS.md` ADR D12.
* **Analysis:**
  - PaySim contains 6,362,620 transactions, of which only 8,213 are fraudulent (~0.129%).
  - In PaySim, fraud occurs **exclusively** in `TRANSFER` and `CASH_OUT` transactions.
  - The synthetic simulator that created PaySim generated fraud by having an agent drain the account balance to zero. In standard Kaggle notebooks, models achieve near-perfect 0.99 AUC by exploiting `newbalanceOrig == 0` and `newbalanceDest`.
  - ADR D12 correctly drops these post-transaction balance columns to prevent data leakage.
  - However, in published machine learning benchmarks on PaySim without post-transaction balance leakage under a strict **time-based split**, achieving a **PR-AUC $\ge$ 0.80** is notoriously difficult because legitimate transfers also frequently drain balances.
  - If the team strictly blocks progress at Gate M2 until hitting PR-AUC 0.80, they risk spending 4+ hours tuning hyperparameters in vain.
* **Recommendation:** Treat PR-AUC $\ge$ 0.80 as a target, but allow an explicit, documented exemption in `progress.md` (e.g., PR-AUC $\ge$ 0.65 with non-leaky features) to keep the hackathon pipeline moving.

#### 3.2. SHAP Attribution vs. Fixed Bucket Logic Contradiction
* **Reference:** `docs/ARCHITECTURE.md` §4; `docs/IMPLEMENTATION_PLAN.md` M2.
* **Contradiction:**
  - Section 4 states: *"Level in {LOW, MEDIUM, HIGH} comes from fixed buckets on the feature value (e.g. amount_to_balance >= 0.9 -> HIGH)"*.
  - But it also states: *"TreeSHAP top-3 features with positive contribution -> (ReasonCode, Level)"*.
  - If the *Level* is determined strictly by the raw feature value (e.g. `amount_to_balance`), what does SHAP actually contribute? SHAP only ranks the features by contribution.
  - What happens if a feature is in the top 3 SHAP contributors, but its absolute contribution is negligible (e.g., +0.0001 log-odds)? The customer would still receive a scary warning about that feature.
  - There must be a minimum contribution threshold (e.g., SHAP value $> +0.1$) before a feature is converted into an active reason code.

---

### 4. LinuxONE (s390x) & Infrastructure Pitfalls

#### 4.1. Unrealistic PyPI Assumption for `cryptography` vs. Ubuntu `apt`
* **Reference:** `docs/IMPLEMENTATION_PLAN.md` M0 Task 4; `docs/DECISIONS.md` ADR D6.
* **The Flaw:** The plan allocates a 30-minute spike to run `pip install cryptography`, expecting it to fail because PyPI lacks an s390x wheel and needs Rust. It then plans to spend hours writing a custom RFC 8032 Ed25519 engine.
* **The Missed Solution:**
  - The VM runs **Ubuntu 24.04 on s390x**.
  - Ubuntu's official package repository has pre-compiled, native s390x packages for `python3-cryptography` and `python3-nacl` (libsodium)!
  - Running `apt-get install -y python3-cryptography` installs a fully compiled, C-accelerated, bug-free Ed25519 library in seconds.
  - Trying to compile Rust crates via `pip` or writing raw curve math (`2^255 - 19` arithmetic) in pure Python during an 18-hour hackathon is an unnecessary high-risk distraction.

#### 4.2. Hardcoded CPU Pinning on 2-vCPU Virtual Machines
* **Reference:** `docs/LINUXONE_RUNBOOK.md` §5; `docs/ARCHITECTURE.md` §8.
* **The Command:**
  ```bash
  docker run -d --name shieldz-api --cpuset-cpus 0-1 ...
  docker run -d --name shieldz-explainer --cpuset-cpus 2-3 ...
  ```
* **The Bug:**
  - LinuxONE Community Cloud (L1CC) student/datathon instances commonly allocate **2 vCPUs** (cores 0 and 1).
  - If `nproc` is 2, running `docker run --cpuset-cpus 2-3` will crash immediately with:
    `docker: Error response from daemon: invalid argument "2-3" for --cpuset-cpus: cpu out of range`.
  - The scripts must dynamically inspect `nproc` or use fractional quotas (`--cpus=1.0`) if fewer than 4 cores exist.

#### 4.3. RAM & Disk Constraints on L1CC VM
* **Dataset Size:** PaySim uncompressed CSV is ~493 MB.
* **Memory Pressure:** Loading 6.3M rows into a pandas DataFrame requires ~1.8 GB RAM. Running feature engineering and XGBoost training will spike memory past 4 GB.
* **Disk Pressure:** The base Jupyter container image is ~5–8 GB. Building another Docker image on top, downloading PaySim, and running Docker builds can easily exhaust a 20 GB root disk.
* **Action:** The team must check `df -h` and `free -h` immediately, and ensure downcasting (`float32`, `int32`, `category`) is used during the PaySim load.

---

### 5. Local Development & Tooling Roadblocks

#### 5.1. Broken `.gitignore` Threatens Invariant I9
* **Reference:** `docs/GIT_WORKFLOW.md` §5; `docs/ARCHITECTURE.md` §6 (Invariant I9).
* **The Bug:**
  - Both documents state that `.gitignore` prevents committing keys, datasets, and artifacts.
  - However, inspecting the actual `.gitignore` file reveals only:
    ```
    reference/
    CLAUDE.md
    ```
  - It does **NOT** ignore `data/`, `artifacts/`, `*.gguf`, `*.pem`, `*.key`, `.venv/`, `__pycache__/`, or `*.sqlite`.
  - If any developer runs a script that generates keys or creates local databases, git will immediately track and stage them. Committing a secret key violates Invariant I9.

#### 5.2. Local Tooling Discrepancies
* **Python Version:** The local environment on this workstation runs **Python 3.13.0**, whereas the project plan strictly mandates **Python 3.12** pinned to match the LinuxONE image.
* **Missing Package Managers:** The instructions in `AGENTS.md` specify:
  `uv venv --python 3.12 && uv pip install -r requirements/local-dev.txt`
  Neither `uv` nor `python3.12` is installed on this machine (`which uv` and `which python3.12` return nothing).
* **Missing Docker Locally:** `docker` is not installed on this local workstation. While the plan is local-first development, container builds must be run either on the remote VM or tested with standard Python scripts locally.

---

### 6. Process & Timeline Critique: The 18-Hour Sprint Trap

#### 6.1. Heavy Process Overhead vs. Elapsed Time
- The team has adopted an extensive handover protocol:
  - Commit `wip(...)`
  - Update `progress.md` snapshot
  - Write a log entry in `progress.md`
  - Write a plain-language story in `explanation.md`
  - Create a docs branch and merge to `main`
  - Allow 20 minutes buffer per handoff
- With 4 team members and multiple sleep shifts, following this rigid ceremony will consume **over 2 to 3 hours** of precious engineering time purely on status administration.
- Currently, more words have been written documenting the plan than all eventual code combined.

#### 6.2. The Sequential Main-Build Baton Bottleneck
- The "Main-build baton" assigns all critical path work (contracts -> features -> model -> API service -> outbox) to **Member 1**.
- If Member 1 runs into issues with feature engineering or model convergence on PaySim, Members 2, 3, and 4 are partially blocked or writing stubs against a contract that has not yet been validated by real data.
- **Recommendation:** Parallelize immediately. Member 1 creates `contracts.py` and `privacy/strip.py`. Member 2 starts on `leak_audit/canaries.py` and `audit/chain.py` simultaneously. Member 3 immediately runs environment probes on the VM.

---

### 7. Actionable Priority Recommendations

| Priority | Area | Action Required |
|---|---|---|
| **P0** | **Git / Security** | Update `.gitignore` immediately to include `data/`, `artifacts/`, `*.pem`, `*.key`, `*.gguf`, `.venv/`, `__pycache__/`, `*.sqlite`. Prevent secret leaks. |
| **P0** | **Scaffolding** | Create the repository skeleton: `pyproject.toml`, `requirements/local-dev.txt`, `Makefile`, and `src/shieldz/contracts.py`. |
| **P1** | **Canary Scanner** | Replace naive 6-digit partial substring matching with bounded word/regex matching to eliminate false positive collisions in `scanner.py`. |
| **P1** | **Prompt & Output Guard** | (a) Add explicit name/string entity checks to the input guard rather than relying solely on "no digits". (b) Relax the output guard so that common numeric conversational idioms (e.g. "within 24 hours", "3 steps") do not discard valid Granite outputs. |
| **P1** | **LinuxONE Crypto** | Do not attempt to compile `cryptography` via `pip`. Install `python3-cryptography` via `apt-get` on Ubuntu s390x to get native hardware-accelerated Ed25519 instantly. |
| **P2** | **Latency & Concurrency** | Move `audit/chain.jsonl` writes and TreeSHAP calculations out of the synchronous locking path, or use batch/checkpoint signing to guarantee `< 50 ms p99`. |
| **P2** | **History Store** | Add a bootstrap/seeding mechanism to `features/history.py` so cold-start transactions don't falsely trigger `NEW_RECIPIENT`. |
| **P2** | **CPU Pinning** | Update runbook and scripts to dynamically read `nproc` before setting `--cpuset-cpus` to avoid container startup crashes on 2-core VMs. |
| **P3** | **Process Streamlining** | Relax documentation ceremony: update `progress.md` only on milestone gate completions rather than every single micro-commit. Focus on building working software. |

---

*Report compiled for Team Marauders. Let's build ShieldZ!*

---

### 8. Resolution log: what was fixed and where

*Added 2026-10-17 ~17:00 IST (Claude Code). Applied in commit `8e58a4d`. The same verdicts are in `docs/DECISIONS.md` → ADR D16.*

| § | Finding | Verdict | Fix | Where |
|---|---|---|---|---|
| 2.1 (1) | "No digits" guard can't catch names or other letter-only PII | ✅ Valid | The input guard now **re-renders the template from the job's enum values and requires a byte-for-byte match**, so no free text of any kind can enter the prompt. "No digits" stays as an extra check on the variable parts. A test that injects a name (letters only) was added to the M5 gate. | `docs/IMPLEMENTATION_PLAN.md` M5 task 2 + gate; `docs/ARCHITECTURE.md` §2 diagram, invariant I2; `monkey_brain.md` §6 |
| 2.1 (2) | Output guard rejects every digit, so Granite would silently always fall back to the template | ✅ Valid | The output guard now rejects only **PII-shaped** content: 4+ digit runs, money amounts (₹/Rs/INR + number), phone-like patterns, URLs, `@`. "24 hours" and "3 steps" are allowed. Every explanation records `source = granite | template`, the UI shows it, and the new M5 gate needs **≥ 80% `source = granite`** on 50 sample jobs. | Plan M5 task 2 + gate; `monkey_brain.md` §6 |
| 2.1 (3) | Prompt template must avoid digits | ✅ Noted | Covered by the re-render rule: the fixed template is ours, and the digit check applies only to the variable parts. | Plan M5 task 2; ARCHITECTURE I2 |
| 2.2 | 6-digit partial rule gives near-certain false positives (timestamps, hashes) | ✅ Valid | A `PARTIAL` is now a **standalone run of 7+ digits** (bounded by non-digits, after joining digit groups split by spaces/dashes) inside a canary number. Digits inside longer runs don't count. New **negative control**: 1,000 decoy canaries are generated but never sent, and a valid run needs **0 decoy hits**. | Plan M4 tasks 3, 5 + gate; `docs/GLOSSARY.md` (partial leak, negative control); `monkey_brain.md` §7 |
| 2.3 (1) | TreeSHAP adds 10–25 ms | ⚠️ Overstated | TreeSHAP for one row over a few hundred depth-6 trees is typically around a millisecond, and the M2 gate already measures `predict + contribs` p99 ≤ 5 ms on the VM. Contributions run only for REVIEW/BLOCK. **Fallback added:** compute codes in the explainer worker from the numeric `FeatureVector` if the budget is missed. | Plan M2 task 4 |
| 2.3 (2) | File lock contention on the audit chain | ⚠️ Partly | The API is one process, so appends use an **in-process lock**. The append is a hash plus a write (microseconds). M6 gate: ≤ 1 ms p99 overhead. | Plan M6 task 1 |
| 2.3 (3) | Pure-Python Ed25519 in the request path breaks 50 ms | ✅ Valid | **Signing never runs in the request path**, for any backend. A background thread signs a checkpoint (chain head) every 100 entries or 1 s. Per-entry signing removed. | Plan M6 task 2, cut order; `docs/DECISIONS.md` D6; ARCHITECTURE §3 step 7 |
| 2.4 | SQLite WAL across two containers on a bind mount | ⚠️ Mostly not an issue | Both containers share one host kernel and a local filesystem, where SQLite locking and WAL shared memory work (the known failures are on network filesystems). Same image, so the same UID owns the files. Added `busy_timeout=5000` and a gate: **5,000 jobs across the containers with 0 `database is locked` errors**. | Plan M3 task 3, M5 gate; DECISIONS D5 |
| 2.5 | Empty history store marks every payee as new | ✅ Valid | The history store is **seeded at startup** (PaySim inbound counts + `src/shieldz/features/demo_seed.csv`) and **bucketed** (0 / 1–3 / 4+) so training and serving see the same scale. New tests: M1 cold-start test; M3 **clean-start bill payment → ALLOW**. | Plan M1 task 5 + gate, M3 gate; ARCHITECTURE §3 feature table |
| 3.1 | PR-AUC ≥ 0.80 may be unreachable without leaky columns | ✅ Valid | 0.80 is now a **target**. Tuning is timeboxed to **45 min**. The **floor** is PR-AUC ≥ 0.50 **and** beating a simple rule baseline (`TRANSFER/CASH_OUT` with `amount_to_balance ≥ 0.99`). Exemptions are recorded in `progress.md`. | Plan M2 gate |
| 3.2 | Tiny SHAP contributions still produce scary reason codes | ✅ Valid | A feature becomes a code only if its contribution is ≥ `MIN_CONTRIB` (start at +0.1 log-odds, tuned). Otherwise the code is `OTHER_PATTERN`. SHAP picks *which* codes; the buckets give the *level*. | Plan M2 task 4; ARCHITECTURE §4 |
| 4.1 | Use Ubuntu's prebuilt `python3-cryptography` instead of compiling | ✅ Valid | apt is now **option 1** in the signing spike: native on the Ubuntu host, and inside the image via a `.pth` file if the base is Debian/Ubuntu. Then `pip` + Rust, then our own RFC 8032. Possible CPACF `KDSA` acceleration noted, to be claimed only if verified. | Plan M0 task 4; DECISIONS D6 + dependency table |
| 4.2 | Hardcoded `--cpuset-cpus 2-3` fails on 2-vCPU VMs | ✅ Valid | The core split is **computed from `nproc`** (≥4 → `0-1` / `2-(n-1)`, 3 → `0` / `1-2`, 2 → `0` / `1`, 1 → no pinning, explainer `--cpus 0.5`). | `docs/LINUXONE_RUNBOOK.md` §5; ARCHITECTURE §8; plan risks table |
| 4.3 | RAM / disk pressure | ⚠️ Already covered | M0 already recorded `free -h` / `df -h`, and the loader uses dtypes. Added an M0 gate item: **≥ 10 GB free before any image build**. | Plan M0 gate |
| 5.1 | `.gitignore` didn't exclude data, keys, artifacts | ✅ Valid | Fixed by the reviewer in `c099122`. Then added `*.sqlite`, `*.sqlite-*`, `.ruff_cache/`, `.ipynb_checkpoints/`, `*.egg-info/`, and an exception `!results/audit_pubkey.pem` so the public key can still be committed. | `.gitignore` |
| 5.2 | Some laptops lack uv / Python 3.12 / Docker | ✅ Valid | `AGENTS.md` now shows the uv install one-liner (uv downloads Python 3.12 itself, no system 3.12 needed) and states that **Docker isn't needed on laptops**. | `AGENTS.md` commands |
| 6.1 | Handoff ceremony costs hours | ⚠️ Partly | Lightened: `progress.md` / `explanation.md`-only commits go **straight to `main`**, logs can be 3–6 lines, and `explanation.md` is needed **only at role/baton handoffs**. | `AGENTS.md` "Before you stop"; `docs/GIT_WORKFLOW.md` §6 |
| 6.2 | Main-build baton is a bottleneck | ⚠️ Partly | The suggested parallel split was already the plan (§3). The real overload was M2 + M3 on one person, so **`model/` moved to Member 3**, with an `Engine` protocol in the M1 contracts and a **stub engine** so M3 starts without waiting for M2. | Plan §3 roles, M1 task 1, M2 heading, M3 task 0; `AGENTS.md`; DECISIONS D16 |
| 1 | Behind schedule, no code yet | ✅ True | No doc change. M0 starts now; per-member first tasks are in `progress.md` → Next action. | `progress.md` |

**New risks added to the plan** (`docs/IMPLEMENTATION_PLAN.md` §7):
- scanner false positives;
- Granite always falling back to the template;
- cold-start history;
- fewer than 4 vCPUs.
