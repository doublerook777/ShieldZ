# ShieldZ

**Marauders_IBM Z Datathon 2026 Project** · Theme 2: *AI Secured: Innovation Without Exposure*

*Real-time payment protection that keeps no personal data. Built on IBM LinuxONE.*

![ShieldZ architecture](docs/assets/architecture.svg)

## Problem statement

Payment scams hit elderly, rural and first-time digital users hardest, and instant payments (UPI, cards, wires) move money in seconds. Fraud AI has two gaps:
1. **Too slow.** A warning after the money has left is useless.
2. **Leaky.** Explaining a block usually means sending names, account numbers and amounts to an AI model or into logs. Fraud detection ends up creating a second privacy problem.

Sourced figures are listed under [Problem statistics](#problem-statistics-cited-in-the-pitch--video) below.

## Proposed solution

ShieldZ makes the decision first, in milliseconds, and keeps personal data out of everything that follows.

- **One door for personal data.** `strip()` is the only code that reads a payment's name, phone, memo and account numbers. It drops the first three and replaces accounts with keyed hashes. Everything after it works on numbers, hashed tokens and fixed reason codes.
- **A decision that never waits.** A trained model scores the payment and returns ALLOW, REVIEW or BLOCK with reason codes, in a few milliseconds. The explanation is written afterwards by a separate container.
- **An AI model that never sees personal data.** IBM Granite rewrites a reviewed template sentence from reason codes. A guard checks the prompt (fixed text, no digits) and the output, and the action sentence ("call your bank on the official number on your card") is always the reviewed one.
- **Proof, not a promise.** The **Canary Leak Audit** sends 1,000 fake customers through the real system and searches every place data lands for them.
- **A record that cannot be quietly rewritten.** Every decision goes into a hash-chained, Ed25519-signed audit trail.

## Key features

- **Real-time decisions:** p99 6.9 ms at one request at a time and 21.8 ms at eight, measured on s390x (limit: 50 ms).
- **Reason codes, not scores:** eight closed codes (for example `ACCOUNT_DRAIN`, `NEW_RECIPIENT`, `LARGE_AMOUNT`). The API never returns the score or any personal data.
- **Privacy you can see:** the demo page shows, for every payment, what you typed next to the record the system kept, and the exact prompt the language model was shown.
- **Language-model explanations with guard rails:** English from Granite, Hindi and Tamil from reviewed templates. If the model fails, loops or says something unsafe, the template is used.
- **Tamper-evident audit trail:** change or delete any entry and verification fails at that exact entry.
- **Platform fit:** API and explainer run as two Docker containers pinned to separate cores of one s390x machine, next to where the data lives.

## Results

All numbers come from files in [`results/`](results/) and were produced on the LinuxONE VM unless noted.

| What | Result | File |
|---|---|---|
| Decision latency, idle | p99 **6.9 ms** (1 at a time), **21.8 ms** (8 at a time); 5,000 requests each | `latency_real.json` |
| Decision latency while Granite is generating | p99 **11.5 ms** and **23.4 ms**, 0 errors | `latency_busy.json` |
| Privacy: Canary Leak Audit | **0 leaks** in 11 places (3.76 MB); planted canaries found 10 of 10; never-sent decoys matched 0 of 1,000 | `leak_scorecard_linuxone.md` |
| Tamper-evident audit trail | 22,086 entries and 190 signatures verified; one append costs p99 0.033 ms | `audit_verify_linuxone.txt`, `audit_append_bench.txt` |
| Granite explanations | 29 of 30 distinct prompts pass the guards; 10 s per fresh generation, instant when cached | `granite_quality.md` |
| Detector | PR-AUC 0.994 and recall 0.999 at 1% false alarms on a time-based holdout | `MODEL_CARD.md` |
| Demo payments (real model) | scam transfer BLOCK 3.8 ms; electricity bill ALLOW 1.5 ms; clinic payment ALLOW 1.4 ms; large transfer to a new account REVIEW 1.6 ms | `z_demo_run.txt` |
| Tests | 140 automated test cases, including the privacy, tamper and guard checks | `tests/` |

**A note on the detector.** PaySim fraud is close to a threshold pattern: a depth-3 decision tree matches our model (`results/baseline_comparison.md`). We do not claim detection accuracy as the contribution. The contribution is the pipeline around the model.

## Tech stack

| Layer | Technology |
|---|---|
| Platform | IBM LinuxONE Community Cloud (s390x), Ubuntu 24.04, Docker, the L1CC Jupyter ML image |
| Language and service | Python 3.12, FastAPI, Uvicorn, Pydantic |
| Detector | XGBoost (JSON model, ONNX export), scikit-learn, pandas, NumPy; trained on PaySim |
| Explanations | IBM Granite 4.0 350M through llama.cpp (CPU) |
| Storage | SQLite in WAL mode (job queue, payee history), JSON-lines files (audit chain, prompt journal) |
| Cryptography | HMAC-SHA256 account tokens; Ed25519 checkpoint signatures (system `python3-cryptography` on s390x, pure-Python RFC 8032 fallback) |
| Front end | Plain HTML, CSS and a little JavaScript, served by the API |
| Quality | pytest (140 cases), ruff, golden-file parity tests, a fuzz test for the prompt guard |

## Running it

On a laptop (no Docker needed):

```bash
uv venv --python 3.12 && uv pip install -r requirements/local-dev.txt
make test          # unit tests
make leak-audit    # canary leak audit (rule-based stand-in engine on a laptop)
```

On the LinuxONE VM:

```bash
make z-build && make z-up                  # build the image, start the API and the explainer
ssh -N -L 8000:localhost:8000 linux1@<vm-ip>   # then open http://localhost:8000/
bash scripts/z_evidence.sh                 # reproduce the VM evidence in results/
```

The full walk-through of the demo page, the proof commands and the tamper demo is in [docs/DEMO_GUIDE.md](docs/DEMO_GUIDE.md).

## Repository map

| Path | What is in it |
|---|---|
| `src/shieldz/privacy/` | `strip()`, keyed tokens, allowlist logging |
| `src/shieldz/service/` | the API, the decision path, the policy rule, the demo page |
| `src/shieldz/model/`, `features/` | training, the XGBoost engine, reason codes, feature engineering |
| `src/shieldz/explainer/` | prompt builder, guards, template texts, Granite wrapper, worker |
| `src/shieldz/audit/` | hash chain, signed checkpoints, verification |
| `src/shieldz/leak_audit/` | canaries, scanner, sinks, scorecard |
| `tests/`, `scripts/`, `results/`, `docs/`, `containers/` | tests, tools, committed evidence, design docs, the image |

Design: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) · Why each choice: [docs/DECISIONS.md](docs/DECISIONS.md)

## Impact

- **Who it protects:** elderly, rural and first-time digital users, who lose the most to scams such as "digital arrest" calls.
- **Who it helps:** banks and payment providers that need fraud defense without creating a second store of customer data.
- **Goals it supports:** SDG 16 (target 16.4, reducing illicit financial flows) and SDG 8 (target 8.10, safer access to banking and financial services).

## Honest limits

- **Synthetic data.** The detector is trained on **PaySim**, which has no age or demographic fields. We claim that the **architecture** protects users and keeps data private. We do not claim measured accuracy for elderly users.
- **A simple model.** On this dataset a small decision tree matches it. A policy rule covers a case the model misses (a large partial transfer to a new payee).
- **English only for the language model.** The 350M model answers in English whatever it is asked, so Hindi and Tamil use reviewed templates.
- **Tamper-evident, not tamper-proof.** The audit trail reveals changes; it cannot prevent them. The newest entries since the last checkpoint cannot be proven complete.
- **The leak audit searches files.** It does not cover memory or the network.
- **The family message is a preview.** Nothing is sent.

## Future enhancements

- Run `strip` in a separate process in front of the API, so the API never holds raw data.
- Copy the signed audit checkpoints to separate storage.
- Real UPI payload formats and a larger, real-world fraud dataset.
- A language model that writes Hindi and Tamil, with the same guard rails.
- Use the platform's AI accelerator for the explainer.

## Team

Marauders: four members, working in a relay across the build window.

## Data and credits

All code was written during the event window (Oct 17–18, 2026). Datasets and open-source libraries used:

| Resource | Use | Link | Licence |
|---|---|---|---|
| PaySim (Kaggle) | Training / evaluation | https://www.kaggle.com/datasets/ealaxi/paysim1 | CC BY 4.0 |
| IBM LinuxONE Community Cloud + Jupyter Lab ML image | Platform | https://github.com/linuxone-community-cloud/jupyter-lab-ml | Apache-2.0 / Community |
| IBM Granite Foundation Models | Explanations | https://github.com/ibm-granite/granite-3.0-language-models | Apache-2.0 |
| XGBoost | Model | https://github.com/dmlc/xgboost | Apache-2.0 |
| llama.cpp / llama-cpp-python | LLM runtime | https://github.com/abetlen/llama-cpp-python | MIT |
| FastAPI, Uvicorn, Pydantic | Service | https://fastapi.tiangolo.com | MIT / BSD |
| Faker | Canary generation | https://github.com/joke2k/faker | MIT |
| pandas, NumPy, scikit-learn | Data / metrics | https://pandas.pydata.org | BSD |
| ONNX, onnxmltools | Model export | https://onnx.ai | Apache-2.0 |
| pytest | Tests | https://pytest.org | MIT |

_Add a row for every new library (rule 5 of the event)._

### Problem statistics cited in the pitch & video:
1. **Reserve Bank of India (RBI) Annual Report 2023–24:** Digital payment fraud cases surged to **36,075 cases** involving **₹1,457 crore** in FY24, with digital channels accounting for over 85% of incidents ([RBI Publications](https://www.rbi.org.in)).
2. **Indian Cyber Crime Coordination Centre (I4C, MHA):** Over **₹1,750 crore** lost to financial cyber scams between Jan–April 2024, with over **₹120 crore** lost specifically to "Digital Arrest" coercion scams targeting senior citizens ([National Cyber Crime Reporting Portal](https://cybercrime.gov.in)).
3. **Federal Trade Commission (FTC) Consumer Sentinel 2023 Data Book:** Consumers reported losing **$10.0 billion** to fraud in 2023. Imposter scams were the #1 reported category. Victims aged 80+ experienced a median loss of **$1,450**—nearly triple younger adults ([FTC Consumer Sentinel](https://www.ftc.gov/reports/consumer-sentinel-network-data-book-2023)).
4. **National Crime Records Bureau (NCRB) Crime in India:** 24.4% year-over-year increase in registered cybercrime, with 69.8% involving financial fraud and deception ([NCRB](https://ncrb.gov.in)).
