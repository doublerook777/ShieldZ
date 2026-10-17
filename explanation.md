# ShieldZ — Plain-Language Explanations

**Who reads this:** a teammate who is about to continue someone else's work, possibly with their own AI agent. They need to understand *what was done and why* in a few minutes, without reading the code.

**Who writes this:** every member or AI agent, **before they stop working or run out of context**. Add a new section at the top (newest first). Don't edit other people's sections, except to fix a factual error (and note that you did).

How it differs from [progress.md](progress.md): `progress.md` is the status board (checkboxes, numbers, next action). This file is the *story*, in simple words.

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
