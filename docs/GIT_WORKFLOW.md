# ShieldZ — Git Workflow

Remote: `git@github.com:doublerook777/ShieldZ.git`. Default branch: `main`.
The model is **trunk-based development with short-lived branches**: small branches that merge back into `main` within hours, never days.

---

## 1. Branches

| Branch | Purpose | Who pushes |
|---|---|---|
| `main` | Always working. `make test` is green on every commit. The LinuxONE VM pulls from here for gates. | Merges only (via PR) |
| `m<N>/<area>-<short-topic>` | One task inside a milestone, e.g. `m2/model-thresholds`, `m4/leak-scanner-variants`, `m5/explainer-guard` | The role that owns those files (plan §3) |
| `fix/<short-topic>` | A bug fix found after a gate | Anyone |
| `docs/<short-topic>` | Docs-only changes, including progress/explanation updates that aren't part of a feature branch | Anyone |

Rules:
- Branch from an up-to-date `main`: `git switch main && git pull --rebase && git switch -c m3/service-outbox`.
- Keep branches **small** (target: under 3 hours of work, under ~400 changed lines). Split anything larger.
- Before opening a PR, rebase onto `main`: `git fetch && git rebase origin/main`. Fix conflicts locally and re-run `make test`.
- **Never force-push `main`.** Force-pushing your own branch after a rebase is fine (`git push --force-with-lease`).
- Nobody commits on the LinuxONE VM. The VM only does `git pull` (see [LINUXONE_RUNBOOK.md](LINUXONE_RUNBOOK.md)).

---

## 2. Commits

Format (a light version of **Conventional Commits**):

```
<type>(<area>): <what changed, imperative, ≤ 72 chars>

<optional body: why, and anything a reviewer must know>
```

`type` ∈ `feat`, `fix`, `test`, `docs`, `refactor`, `perf`, `chore`, `wip`
`area` ∈ `contracts`, `privacy`, `features`, `model`, `service`, `outbox`, `explainer`, `audit`, `leak-audit`, `ui`, `infra`, `docs`, `progress`

Examples:
```
feat(leak-audit): detect base64 and hex variants of canary values
perf(service): set nthread=1 for single-row inference (p99 41ms → 12ms)
docs(progress): M3 gate passed on VM, latency numbers added
wip(explainer): guard rejects digits; output guard not done yet
```

- `wip:` commits are allowed **on branches only**, especially right before a handoff, so nothing is lost. They are squashed away on merge.
- Commit often (at least every ~45 min of work), so a lost laptop or agent context costs little.

---

## 3. Pull requests

1. Push the branch and open a PR to `main` (GitHub web UI, or `gh pr create` if installed).
2. PR description, copy this:
   ```
   ## What
   ## Why / milestone
   M<N> — <task>
   ## How I tested
   - [ ] make test (local)
   - [ ] make z-gate on VM (required if the PR touches deps, containers, model, or is a gate PR)
   ## Invariants touched (I1–I9 in ARCHITECTURE.md §6)
   ## progress.md / explanation.md updated?
   ```
3. **Review:** one other member looks at it, by default Member 4 (Pitch & review), 10 minutes max; it's a hackathon. If nobody is free within 20 minutes and `make test` is green, the author may self-merge, **except** for PRs touching `contracts.py`, `privacy/`, `explainer/guard.py` or `leak_audit/`. Those always need a second pair of eyes because they hold the privacy claim.
4. Merge with **Squash and merge**. The squash message follows §2.
5. Delete the branch after merging.

---

## 4. Milestone tags

When a milestone gate passes (all boxes ticked in `progress.md`, Z gate run on the VM against that exact commit):

```bash
git switch main && git pull
git tag -a m3-gate -m "M3 gate passed: p99 23.4 ms @c=8 on LinuxONE (results/latency_m3.json)"
git push origin m3-gate
```

Tags give everyone a known-good point to go back to: `git switch --detach m3-gate`.

---

## 5. What never gets committed

`.gitignore` covers these (set up in M0). Check before every push: `git status`.

| Never commit | Why |
|---|---|
| `data/` (PaySim CSV, samples) | Large; licence says link, not redistribute |
| `artifacts/` (models, SQLite, logs, audit chain) | Generated; may contain test PII from runs |
| `artifacts/keys/` (pepper, signing private key) | Secrets |
| `*.gguf` (Granite weights) | Huge; lives in the image |
| `.venv/`, `__pycache__/`, `.ipynb_checkpoints/` | Local junk |
| Notebook outputs with real-looking personal data | Use **Restart & Clear Output** unless it's an evidence notebook with synthetic data only |

**Do** commit `results/` (metrics, latency JSON, scorecards, model card, audit public key). These are the evidence for the video.

Note: `CLAUDE.md` and `reference/` are currently listed in `.gitignore` (team decision). The agent rules that everyone needs live in the committed `AGENTS.md`.

---

## 6. Handoff commits (when you stop working)

Before you hand off, whether you're a human or an agent running out of context:

1. Commit everything on your branch, even half-done work: `wip(<area>): <state>`.
2. Push the branch.
3. Update `progress.md` (status snapshot plus a short log entry). Add an `explanation.md` section only if you're handing over a role or the baton.
4. Commit `progress.md` / `explanation.md`-only changes **directly to `main`** (`git pull --rebase && git commit && git push`). This is the one exception to the PR rule, because they're notes, not code. `progress.md` on `main` must always be current.

If two people edit `progress.md` at once, the conflict is easy to fix: keep both log entries, newest first.

**Passing the main-build baton mid-branch.** If the task isn't finished, don't merge. Push the `wip` branch and name it in `progress.md`. The receiver continues **on the same branch**: `git fetch && git switch m3/service-outbox && git pull`. Only one person commits to a branch at a time, the current holder.
