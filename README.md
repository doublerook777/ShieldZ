# ShieldZ

**Marauders_IBM Z Datathon 2026 Project** · Theme 2: *AI Secured — Innovation Without Exposure*

*Privacy-preserving, real-time scam and fraud defense for vulnerable users, built on IBM LinuxONE.*

> Status: planning complete, build in progress. See [progress.md](progress.md).

## The problem

Payment scams hit elderly, rural and first-time digital users hardest, and instant payments (UPI, cards, wires) move money in seconds. Fraud AI has two gaps:
1. **Too slow:** a warning after the money has left is useless.
2. **Leaky:** explaining a block often means sending names, account numbers and amounts to an AI model or into logs, which creates a second privacy risk.

## What ShieldZ does

- **Decides in real time.** An XGBoost model scores each payment and returns allow / review / block, targeting **< 50 ms p99 on LinuxONE**.
- **Explains without exposure.** IBM Granite writes a calm, plain-language warning from fixed **reason codes only** (e.g. `ACCOUNT_DRAIN`, `NEW_RECIPIENT`). It never sees names, account numbers or amounts.
- **Proves it.** The **Canary Leak Audit** pushes 1,000 fake identities through the whole system and scans every log, database, prompt and response for them, including encoded and hashed forms. Result: a measured "0 leaks" scorecard, with a positive control that proves the scanner works.
- **Can't be quietly rewritten.** Every decision goes into a hash-chained, Ed25519-signed audit log.

Architecture: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) · Plan: [docs/IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md) · Explained simply: [monkey_brain.md](monkey_brain.md)

## Why IBM Z / LinuxONE

Scoring and generative AI run next to the transaction data on one s390x machine, in Docker containers pinned to separate cores. Granite runs through llama.cpp with IBM zDNN/NNPA acceleration. No personal data is sent to an outside AI service.

## Results

_To be filled from `results/` after the gates pass: model metrics, p50/p99 latency on LinuxONE, leak scorecard, tamper test._

## Running it

_Filled in during M3/M7. Short version: see [docs/LINUXONE_RUNBOOK.md](docs/LINUXONE_RUNBOOK.md) and `make z-up`._

## Honest limits

The detector is trained on **PaySim**, a synthetic dataset with no age or demographic fields. We claim that the **architecture** protects users and keeps data private. We don't claim measured accuracy for elderly users.

## Data and credits

All code was written during the event window (Oct 17–18, 2026). Datasets and open-source libraries used:

| Resource | Use | Link | Licence |
|---|---|---|---|
| PaySim (Kaggle) | Training / evaluation | https://www.kaggle.com/datasets/ealaxi/paysim1 | _TODO: confirm in M0_ |
| IBM LinuxONE Community Cloud + Jupyter Lab ML image | Platform | https://github.com/linuxone-community-cloud/jupyter-lab-ml | — |
| IBM Granite | Explanations | _TODO: exact model link (M0)_ | Apache-2.0 (verify) |
| XGBoost | Model | https://github.com/dmlc/xgboost | Apache-2.0 |
| llama.cpp / llama-cpp-python | LLM runtime | https://github.com/abetlen/llama-cpp-python | MIT |
| FastAPI, Uvicorn, Pydantic | Service | https://fastapi.tiangolo.com | MIT / BSD |
| Faker | Canary generation | https://github.com/joke2k/faker | MIT |
| pandas, NumPy, scikit-learn | Data / metrics | https://pandas.pydata.org | BSD |
| ONNX, onnxmltools | Model export | https://onnx.ai | Apache-2.0 |
| pytest | Tests | https://pytest.org | MIT |

_Add a row for every new library (rule 5 of the event)._

Problem statistics used in the pitch (FTC Consumer Sentinel, RBI, NCRB) are cited with links in the video and here: _TODO_.
