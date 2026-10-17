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
