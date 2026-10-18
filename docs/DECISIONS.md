# ShieldZ — Decision Log

Short **ADR** entries: what we decided, why, and what would change our minds. Status values:
- *Accepted*: decided.
- *Pending M0*: waits on an M0 spike result.
- *Superseded*: replaced by a later entry.

Add new entries at the bottom and never rewrite old ones. Supersede them instead.

Evidence gathered on 2026-10-17 from PyPI and the `linuxone-community-cloud/jupyter-lab-ml` repo (its `packages.txt` and the Lab notebooks):

| Package | s390x status | Consequence |
|---|---|---|
| onnxruntime 1.31 | **no s390x wheel, no sdist** | Can't serve ONNX on Z without a large source build |
| shap 0.54 | no s390x wheel (sdist only, C++ build) | Use XGBoost's built-in TreeSHAP instead |
| cryptography 50.x | no s390x wheel on PyPI (sdist needs Rust); **Ubuntu ships `python3-cryptography` for s390x via apt** | Try apt first (ADR D6) |
| pynacl | no s390x wheel | Same as above |
| snapml 1.17.2 | **cp312 s390x wheel exists** | Candidate Z-optimised tree inference |
| pydantic-core 2.50 | cp312 s390x wheel | FastAPI works |
| fastapi, uvicorn, faker, pytest, onnxmltools | pure Python | Install freely |
| uvloop, httptools | sdist only | Not needed; plain asyncio is fine |
| xgboost 3.4.1, numpy 2.0.2, pandas 3.0.6, scikit-learn 1.9.0, onnx 1.22.0, skl2onnx, tf2onnx, torch 2.11 (cpu), transformers 5.19, llama_cpp_python 0.3.36, huggingface_hub, httpx 0.28.1, ibm-zdnn-plugin | **preinstalled in the L1CC Jupyter image** (Python 3.12, `/opt/venv`) | Use as-is; pin the laptop venv to the same versions |
| pyarrow | **not** in the image | No parquet; use CSV(.gz) |

---

## D1 — Development workflow: local-first, gated on LinuxONE · *Accepted*
Code and unit tests run on laptops. Every milestone gate also runs on the LinuxONE VM (`make z-gate`), and training, benchmarks, Granite, the official Leak Audit and evidence are produced on the VM.
**Why:** fast iteration locally, and s390x surprises get caught within hours. The judges reward real use of LinuxONE.
**Rejected:** "build everything locally, upload at the end" (s390x risk too late); "develop only in Jupyter on the VM" (slow, hard to test, notebooks don't merge in git).

## D2 — Inference engine: XGBoost native on Z; ONNX is an export only · *Accepted*
The decision service scores with XGBoost `Booster.inplace_predict` (preinstalled, `nthread=1` for single rows). The M0 spike confirmed that Snap ML (`snapml==1.17.2`) installs and imports cleanly on s390x with `libsnapmllocal3_zdnn` accelerator support. M2 will benchmark Snap ML against XGBoost and keep the faster one. The model is also exported to ONNX (onnxmltools) and checked with `onnx.checker` to show portability ("train anywhere, deploy on Z").

## D3 — Explanations: XGBoost `pred_contribs` instead of the `shap` package · *Accepted*
`booster.predict(dmatrix, pred_contribs=True)` returns exact TreeSHAP values, the same maths the `shap` library uses for trees, with no extra dependency.
**Why:** shap has no s390x wheel; this is faster and already installed.

## D4 — LLM: Granite GGUF via llama_cpp_python from the Lab 2 image · *Accepted (confirmed: granite-4.0-h-350m-base-be.f16 @ 3.82 tok/s)*
The M0 spike located the Granite model at `/home/ibm-user/granite-4.0-h-350m-base-be.f16.gguf`. Loaded via `llama_cpp.Llama(n_ctx=512)` in 8.67 s and generated 60 tokens at 3.82 tokens/second. The worker runs in its own container. `TemplateExplainer` is the local stand-in and the runtime fallback.
**Rule:** read the Lab 2 code only to learn the model path and settings; **write our own code** (event rule: no copied code).

## D5 — Queue: SQLite outbox · *Accepted*
The decision path inserts a row into `explain_jobs` (SQLite, WAL mode). The explainer polls it.
**Why:** standard library only, durable, inspectable, easy to scan for leaks, works across two containers that share a bind mount on one host.
Both containers share one host kernel and a local filesystem, so SQLite's locks and WAL shared memory work across them (the known problems are with network filesystems). We set `busy_timeout=5000`. Both containers use the same image, so the same UID owns the files. Verified by the M5 cross-container gate.
**Rejected:** Redis/Kafka/RabbitMQ (extra services and s390x images to verify); an in-process asyncio queue (the LLM would compete for the API's CPU).

## D6 — Signing backend for the audit chain · *Accepted (Option 1: apt python3-cryptography / pure-Python RFC 8032)*
The M0 signing spike confirmed:
- Option 1 (`apt-get install -y python3-cryptography`): **Works** (Ubuntu host has version `41.0.7`).
- Option 2 (`pip install cryptography`): **Fails** (no s390x wheel on PyPI; source build fails missing openssl headers).
- Option 3: Pure Python RFC 8032 Ed25519 remains available as zero-dependency fallback.
Whatever the backend, **signing runs in a background thread, never in the request path.** It signs a checkpoint (the chain head hash) every 100 entries or every second.

## D7 — Container base image: the L1CC Jupyter image · *Accepted*
`containers/Containerfile` starts `FROM registry.linuxone.cloud.marist.edu/l1cc/jupyterlab-image-s390x:latest`, which is already pulled on the VM.
**Why:** it already has a working s390x Python 3.12 ML stack (xgboost, llama.cpp with zDNN). Rebuilding that ourselves would cost hours.
**Cost:** a large image. That's acceptable for a demo.

## D8 — No public API port; use an SSH tunnel · *Accepted*
The API listens on `127.0.0.1:8000` on the VM. Laptops use `ssh -L 8000:localhost:8000 ...`.
**Why:** a "no exposure" project shouldn't expose an unauthenticated API to the internet. It also means no firewall changes.

## D9 — Portable formats · *Accepted*
Models are saved as XGBoost JSON (`model.json`), data as CSV(.gz) and results as JSON/Markdown. No pickle across machines, no parquet.
**Why:** s390x is big-endian; JSON is byte-order independent. pyarrow isn't in the image.

## D10 — PII tokenization: HMAC-SHA256 with a secret pepper · *Accepted*
Account identifiers become `HMAC(pepper, id)` tokens. The pepper is generated on first run into `artifacts/keys/pepper` and never committed.
**Why:** a plain hash of an account number can be reversed by trying every account number. A keyed HMAC cannot be reversed without the key. The Leak Audit flags unsalted hashes of canaries as leaks.

## D11 — Thin notebooks · *Accepted*
Notebooks import from `src/shieldz` and only orchestrate and display.
**Why:** logic in notebooks can't be unit-tested or merged cleanly, and would diverge from what the service runs.

## D12 — Decision-time features only · *Accepted*
PaySim's `newbalanceOrig`/`newbalanceDest` (and anything derived from them) are excluded from training.
**Why:** a bank doesn't know post-transaction balances before the transaction executes. Using them inflates metrics (data leakage), and the serving path couldn't compute them.

## D13 — Explanations for Hindi/Tamil · *Accepted: templates (see D18)*
English comes from Granite. For Hindi/Tamil we first test Granite's output quality; if it's poor, we use human-reviewed static templates per reason code.
**Why:** Granite isn't officially trained on Hindi/Tamil, and a wrong warning to a vulnerable user is worse than a simple one.
**Outcome (2026-10-18):** tested on s390x: the 350M model answers in English whatever the language line says, so Hindi and Tamil use the human-written templates (D18).

---

## D14 — Container runtime: Docker on Ubuntu 24.04 · *Accepted (confirmed: Ubuntu 24.04-Datathon, Docker 29.8.0)*
The team set up the VM by following the Ubuntu 24.04 + Docker path of the jupyter-lab-ml README. We use Docker, not Podman:
- no pods: `shieldz-api` and `shieldz-explainer` both run with `--network host`;
- the API binds `127.0.0.1:8000` (ADR D8 still holds);
- CPU pinning uses `--cpuset-cpus`, which the rootful Docker daemon supports.

The original idea said Podman. For judging, both count as "containerization".

## D15 — Team model: hybrid relay with 4 members · *Accepted*
The critical path is one "main build" passed between members (the baton). Proof build, LinuxONE operations and pitch/review run in parallel in separate folders (plan §3).
**Rejected:** a pure relay (only one person productive, 2–3 h lost to handoffs); four parallel lanes (merge conflicts and too much dependency early on).

## D16 — Response to the 16:30 review (`conversation.md`) · *Accepted*
Each critique point, what we changed, or why we didn't:

| # | Point | Verdict | Change |
|---|---|---|---|
| 2.1 | "No digits" doesn't stop names | **Valid** | Guard now re-renders the template and compares byte for byte (I2). Name-injection test added (M5) |
| 2.1 | Output guard rejects all digits, so Granite would always fall back | **Valid** | Output guard targets PII shapes; `source` field; ≥ 80% Granite gate (M5) |
| 2.2 | 6-digit partial rule causes false positives | **Valid** | Standalone 7+ digit rule + negative control with never-sent decoys (M4) |
| 2.3 | TreeSHAP costs 10–25 ms | Overstated: TreeSHAP for one row on a few hundred shallow trees is typically about a millisecond | Already gated (M2 engine p99 ≤ 5 ms incl. contribs); fallback to worker-side codes added |
| 2.3 | File lock + signing in request path | **Valid for signing** | Signing moved to a background checkpoint thread for every backend (D6). Append stays: microseconds |
| 2.4 | SQLite across containers on bind mounts | Mostly not an issue on one host/local filesystem | `busy_timeout`, same UID, cross-container gate (M5) |
| 2.5 | Cold-start history marks every payee new | **Valid** | Seeded + bucketed history; clean-start ALLOW test (M1, M3) |
| 3.1 | PR-AUC 0.80 may be unreachable without leaky columns | **Valid** | 45-min tuning timebox; floor = PR-AUC ≥ 0.50 and beat a rule baseline |
| 3.2 | Tiny SHAP contributions still produce scary codes | **Valid** | `MIN_CONTRIB` threshold, else `OTHER_PATTERN` |
| 4.1 | Use Ubuntu's `python3-cryptography` | **Valid** | apt is now the first option (D6, M0 task 4) |
| 4.2 | Hardcoded `--cpuset-cpus 2-3` fails on 2 vCPUs | **Valid** | `make z-up` computes the split from `nproc` |
| 4.3 | RAM/disk pressure | Already covered (M0 facts, dtypes) | Added a `df -h` ≥ 10 GB check to the M0 gate |
| 5.1 | `.gitignore` incomplete | **Valid** | Fixed in `c099122`; `*.sqlite` and the audit public-key exception added after |
| 5.2 | Some laptops lack uv / Python 3.12 / Docker | **Valid** | AGENTS.md: install uv (it fetches Python 3.12 itself); Docker isn't needed on laptops |
| 6.1 | Handoff ceremony costs hours | **Partly** | progress/explanation-only commits may go straight to `main`; `explanation.md` only at role/baton handoffs |
| 6.2 | Baton bottleneck; "parallelise immediately" | The parallel split it proposes is already the plan (§3). The real load issue is M2 + M3 both sitting on the main build | **Done:** `model/` moved to Member 3 (LinuxONE operator), with an `Engine` protocol in contracts and a stub engine for M3 |

## Adding a dependency (process)
1. `python scripts/check_deps.py <package>` (or check PyPI for an `s390x` wheel / `none-any` wheel).
2. Add a row to the table above with the result.
3. Add it to `requirements/z-extra.txt` (VM) and `requirements/local-dev.txt` (laptop), with exact versions.
4. Rebuild the image on the VM and run `make z-gate` **before** merging.
5. Add a credit line with a link in `README.md` (event rule).

## D17 — A policy rule next to the model makes REVIEW reachable · *Accepted (revised 2026-10-18)*
The trained XGBoost model has two modes on our features: a full-account drain scores about 0.97 and almost everything else 0.03-0.15 (PaySim fraud is almost entirely "drain the account"). Measured on the VM: a transfer of half the balance (Rs 2,45,000 of 4,90,000) to a brand-new payee at 11 PM scores 0.125, so the model alone would ALLOW it. Real scams often take a large share of someone's savings without emptying the account.
**Decision:** `service/decide.py::apply_policy` raises an ALLOW to REVIEW (reasons `NEW_RECIPIENT` and `LARGE_AMOUNT`) only when **all** hold: the payee has no history, the amount is at least `review_new_payee_ratio` of the payer's balance (default 0.4), and at least `review_new_payee_min_amount` rupees (default 10,000). A `null` ratio in `artifacts/model/thresholds.json` disables it. It never lowers a decision.
**History:** the first version held *any* first payment of Rs 5,000 or more to a new payee. That added friction to ordinary payments (an Rs 8,500 clinic bill), and it was dropped the same day after review: paying someone new is normal, so the rule now targets only a large share of the balance.
**Consequences:** a payee counts as known after one payment, so the demo uses a fresh payee per press. The video describes REVIEW as "model plus a policy rule". Demo scenario D is the REVIEW example; scenario C (the clinic payment) is an ordinary ALLOW.

## D18 — Granite 350M rewrites the English "why"; the action is always the template's · *Accepted* (resolves D13's Granite part)
Measured on s390x: asked to write a warning from the reason codes, the 350M base model looped ("Do not mention ...") or stated falsehoods; asked to rewrite the template text it gave good explanations but told the customer to call "their number" in all 30 samples, which in a digital-arrest scam is the scammer's number.
**Decision:** the prompt asks Granite to rewrite the English template sentence in simple words (two fixed examples, no digits). `compose_explanation` keeps the model's explanation sentences, drops everything from its first advice sentence on, and appends the template's fixed action ("call your bank on the official number on your card"). `validate_quality` rejects loops, contradictions and missing advice. Only English jobs go to the LLM; Hindi and Tamil use the human-written templates (a 350M base model answers in English whatever the language line says). Output is cached by prompt hash (`llm_cache` in `outbox.sqlite`, an existing registered sink); the queue is newest-first.
**Evidence:** `results/granite_quality.md`: 28 of 30 distinct prompts accepted (93%), 10.4 s p50 per fresh generation. The video must say the texts are generated once per reason combination and cached, and that the action sentence is a reviewed template.

