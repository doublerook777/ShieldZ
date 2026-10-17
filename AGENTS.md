# AGENTS.md — working rules for ShieldZ

For AI coding agents (Claude Code, Gemini, Copilot, …) **and** the humans driving them. Keep it short and current. The details live in `docs/`.

Claude Code users: `CLAUDE.md` is gitignored (C-003). Create a local `CLAUDE.md` containing just `@AGENTS.md` so Claude Code loads these rules.

The repo is **private for now and goes public before submission** (C-002). Treat everything you commit as public: the never-commit list below is strict.

## Start of every session
1. Read `progress.md` (status snapshot + newest log entries).
2. Read the newest 1–2 entries in `explanation.md`.
3. Check the index in `conversation.md` for 🟡 open / 🔵 answered threads addressed to your role or member, and answer what you can.
4. Find your milestone in `docs/IMPLEMENTATION_PLAN.md` and work toward **its gate checklist**.
5. `git switch main && git pull --rebase`, then branch per `docs/GIT_WORKFLOW.md` (`m<N>/<area>-<topic>`).
6. Check **which role you are** (and whether you hold the main-build baton) in the `progress.md` snapshot. Edit only the files your role owns (plan §3).

## Before you stop (or when context is running low): mandatory
1. Commit everything on your branch (a `wip(<area>): …` commit is fine) and push.
2. Update the **status snapshot** in `progress.md` and add a short **log entry** (3–6 lines is fine).
3. **Only when handing a role or the baton to someone else** (shift change, tokens out, leaving): also add a plain-language section at the top of `explanation.md`. Routine pushes don't need one.
4. Reply to any `conversation.md` thread you were working on. Open a new thread for any question you couldn't settle.
5. Commit `progress.md` / `explanation.md` / `conversation.md`-only changes **directly to `main`** (`git pull --rebase` first). No branch or PR is needed for notes.
If you're an agent and your context is nearly full, do this **now**, before attempting more work.

## Project state
The project is in the planning-complete stage and no application code exists yet. The commands below are **planned** and created in M0. If a target doesn't exist yet, the milestone that creates it hasn't landed.

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh                        # only if uv is missing; uv fetches Python 3.12 itself
uv venv --python 3.12 && uv pip install -r requirements/local-dev.txt   # laptop env (versions pinned to the LinuxONE image)
# Docker is NOT needed on laptops: images are built on the VM only.
make test            # pytest -m "not z and not llm" — run before every push
pytest tests/unit/test_strip.py::test_no_pii_in_output   # single test
make lint            # ruff check + ruff format --check
make leak-audit      # canary Leak Audit (template explainer locally)
# on the LinuxONE VM only (see docs/LINUXONE_RUNBOOK.md):
make z-build && make z-gate      # milestone gate on s390x
make z-up / make z-down          # run / stop the api + explainer Docker containers
```

## Non-negotiable rules
- **Invariants I1–I9** (`docs/ARCHITECTURE.md` §6) must hold after every change. The core ones:
  - only `privacy.strip()` sees PII;
  - the LLM prompt is template + enum values with **no digits**;
  - the decision path never waits on the LLM;
  - logs use a field allowlist;
  - every new data sink gets registered in `leak_audit/sinks.py`.
- **s390x:** no new dependency without checking that it has an s390x wheel, is pure Python, or is preinstalled in the L1CC image. Record it in the `docs/DECISIONS.md` table. onnxruntime, shap and cryptography have **no** s390x wheels.
- **Event rules:** all code is written from scratch during the event (Oct 17–18, 2026). Don't paste code from the L1CC Lab notebooks, from `loan_demo/` or from other projects; read them only to learn settings. Credit every library and dataset with a link in `README.md`.
- Don't use PaySim's post-transaction balance columns as features (ADR D12).
- Models are saved as XGBoost JSON and data as CSV. No pickle across machines, no parquet.
- Never commit `data/`, `artifacts/`, keys, `*.gguf`. Do commit `results/`.
- `contracts.py` is frozen after the M1 gate. Changing it needs a PR acknowledged by every member.
- PRs touching `contracts.py`, `privacy/`, `explainer/guard.py` or `leak_audit/` always need a human reviewer.
- If a question is the team's call (scope, trade-offs, priorities) rather than something the code or docs answer, **don't guess**: open a thread in `conversation.md` (template in the file) and keep working on something else.

## Team model (4 members, hybrid; details in plan §3)
| Role | Default | Owns |
|---|---|---|
| Main build (**baton**, one holder at a time) | Member 1 | contracts, privacy, features, service app/decide, outbox, containers, Makefile, pyproject, requirements |
| Proof build | Member 2 | `leak_audit/`, `audit/`, `explainer/{prompt,guard,template,journal}.py` |
| LinuxONE operator | Member 3 | `model/`, `scripts/`, `notebooks/`, `explainer/{granite,worker}.py`, `results/`, all Z gates |
| Pitch & review | Member 4 | README, `docs/assets/`, `service/static/`, demo scenarios, PR reviews, night relief |

The VM is **Ubuntu 24.04 + Docker** (ADR D14). Use `docker`, not `podman`.

## Where things are
| Need | File |
|---|---|
| What to build next, gates | `docs/IMPLEMENTATION_PLAN.md` |
| How the parts connect, file structure | `docs/ARCHITECTURE.md` |
| Why a tool was chosen | `docs/DECISIONS.md` |
| A word you don't know | `docs/GLOSSARY.md` |
| The whole project in simple terms, with pictures | `monkey_brain.md` |
| Critiques, questions, proposals, blockers between members | `conversation.md` |
| Branch / commit / PR rules | `docs/GIT_WORKFLOW.md` |
| VM, Jupyter, Docker, tunnels | `docs/LINUXONE_RUNBOOK.md` |
