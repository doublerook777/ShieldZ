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

## 2026-10-17 19:45 IST — Member 4 (Antigravity) — Pitch, UI & Demo Scenarios (M7 / M8)

**In one sentence:** I created the 3 realistic demo stories (including the "Digital Arrest" scam), built a responsive single-page demo UI that runs on LinuxONE with zero external dependencies, researched real-world scam statistics from RBI/I4C/FTC, and wrote the complete 3-minute video presentation storyboard.

**What I built or changed (simple words):**
- `scripts/demo_scenarios.py`: 3 scripted end-to-end stories:
  - Scenario A: 72-year-old Savitri Devi coerced via Skype by fake police into transferring ₹4.85 lakh (99% balance) to a fake escrow &rarr; **BLOCK** in <5 ms.
  - Scenario B: Regular ₹1,840.50 electricity bill to a known utility provider &rarr; **ALLOW**.
  - Scenario C: Urgent ₹8,500 clinic diagnostics payment to a new clinic while traveling &rarr; **REVIEW**.
  - Added CLI runner (`--list`, `--show`, `--json`, `--verify`, `--run`).
- `src/shieldz/service/static/index.html`: A self-contained dark-mode dashboard that works completely offline. It pre-fills scenarios, shows an instant decision hero badge with server timing, displays TreeSHAP reason codes, polls IBM Granite for the plain-language warning, renders simulated family SMS alerts, and displays the measured Canary Leak Audit scorecard.
- `docs/assets/pitch_research.md`: Sourced statistics (₹1,750+ Cr lost in Q1 2024 to cyber scams, $10B FTC losses, senior citizen impact) and a second-by-second 3:00 video storyboard.
- `README.md`: Verified PaySim CC BY 4.0 license, IBM Granite details, and scam citations.
- Opened thread `C-005` in `conversation.md` asking Member 1 to mount `static/` in `service/app.py`.

**Why it's done this way:**
- Offline UI: In hackathons or behind SSH tunnels on LinuxONE, CDNs often fail or add latency. Having self-contained vanilla CSS and JS means the demo is rock-solid under all conditions.
- Realistic scenarios: Grounding the demo in real RBI and I4C "Digital Arrest" advisories gives judges immediate recognition of the problem.

**How to see it working:**
    .venv/bin/python scripts/demo_scenarios.py --verify
    .venv/bin/python scripts/demo_scenarios.py --list
    Open `src/shieldz/service/static/index.html` in any browser

**What's not done / known problems:**
- `service/app.py` does not yet mount `service/static` (C-005 opened for Member 1). The HTML file can still be opened directly in a browser.

**If I were continuing, I would next:**
1. Stand by for PR reviews as other members submit M5, M6, and M2.
2. Rehearse the 3-minute video script.

**Files to look at first:** `scripts/demo_scenarios.py`, `src/shieldz/service/static/index.html`, `docs/assets/pitch_research.md`

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
