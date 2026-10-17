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
| cryptography 50.x | no s390x wheel (sdist needs Rust) | Ed25519 needs a spike or our own implementation |
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

## D2 — Inference engine: XGBoost native on Z; ONNX is an export only · *Pending M0 (Snap ML part)*
The decision service scores with XGBoost `Booster.inplace_predict` (preinstalled, `nthread=1` for single rows). If the M0 spike shows that Snap ML imports on the VM, M2 benchmarks Snap ML (importing the XGBoost JSON model) against XGBoost and keeps the faster one. The model is also exported to ONNX (onnxmltools) and checked with `onnx.checker` to show portability ("train anywhere, deploy on Z").
**Changed from the original idea**, which served ONNX via ONNX Runtime. onnxruntime has no s390x distribution on PyPI.
**Would revisit if:** an s390x onnxruntime build turns out to be available in the image or via dnf.

## D3 — Explanations: XGBoost `pred_contribs` instead of the `shap` package · *Accepted*
`booster.predict(dmatrix, pred_contribs=True)` returns exact TreeSHAP values, the same maths the `shap` library uses for trees, with no extra dependency.
**Why:** shap has no s390x wheel; this is faster and already installed.

## D4 — LLM: Granite GGUF via llama_cpp_python from the Lab 2 image · *Pending M0 (model identity)*
We reuse the Granite model file and the llama.cpp build (with zDNN/NNPA and OpenBLAS) that ship with the L1CC image for the mandatory Lab 2. The worker runs in its own container. `TemplateExplainer` is the local stand-in and the runtime fallback.
**Rule:** read the Lab 2 code only to learn the model path and settings; **write our own code** (event rule: no copied code).

## D5 — Queue: SQLite outbox · *Accepted*
The decision path inserts a row into `explain_jobs` (SQLite, WAL mode). The explainer polls it.
**Why:** standard library only, durable, inspectable, easy to scan for leaks, works across two containers that share a bind mount on one host.
**Rejected:** Redis/Kafka/RabbitMQ (extra services and s390x images to verify); an in-process asyncio queue (the LLM would compete for the API's CPU).

## D6 — Signing backend for the audit chain · *Pending M0*
- If `pip install cryptography` builds in the image within 30 min: use its Ed25519 and **sign every entry**.
- Otherwise: write our own Ed25519 from **RFC 8032** (pure Python, the hashing comes from `hashlib`). It must pass all RFC 8032 §7.1 test vectors. Because it's slower, **sign checkpoints** (chain head) every 100 entries or 1 s.
- Post-quantum ML-DSA (Dilithium) via liboqs: a 90-min stretch only after the M3–M5 gates pass.

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

## D13 — Explanations for Hindi/Tamil · *Pending M5*
English comes from Granite. For Hindi/Tamil we first test Granite's output quality; if it's poor, we use human-reviewed static templates per reason code.
**Why:** Granite isn't officially trained on Hindi/Tamil, and a wrong warning to a vulnerable user is worse than a simple one.

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

## Adding a dependency (process)
1. `python scripts/check_deps.py <package>` (or check PyPI for an `s390x` wheel / `none-any` wheel).
2. Add a row to the table above with the result.
3. Add it to `requirements/z-extra.txt` (VM) and `requirements/local-dev.txt` (laptop), with exact versions.
4. Rebuild the image on the VM and run `make z-gate` **before** merging.
5. Add a credit line with a link in `README.md` (event rule).
