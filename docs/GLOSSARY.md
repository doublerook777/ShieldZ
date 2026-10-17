# ShieldZ — Glossary

Plain-language explanations of every technical term used in the ShieldZ docs. Grouped by topic; each entry says **what it is** and **why it matters to ShieldZ**. If you add a new term to any doc, add it here.

---

## 1. The platform: IBM Z and LinuxONE

| Term | What it is | Why it matters here |
|---|---|---|
| **IBM Z / mainframe** | IBM's enterprise computers, built to handle huge volumes of transactions reliably and securely. Most of the world's card payments touch one. | Fraud checks belong where the payments already run. |
| **LinuxONE** | IBM's line of Z machines that run only Linux. | The Datathon gives us a LinuxONE VM. |
| **LinuxONE Community Cloud (L1CC)** | A free cloud run by Marist University where students get LinuxONE VMs. | Our VM, our Jupyter container and our demo all run here. |
| **VM (virtual machine)** | A computer simulated in software on a bigger machine. | Our "LinuxONE computer" is a VM; we SSH into it as user `linux1`. |
| **s390x** | The name of the IBM Z CPU architecture (like `x86_64` for most laptops, `arm64` for Macs). | Software must be built for s390x. Many Python packages aren't, so we check every dependency. |
| **Big-endian / little-endian (endianness)** | The order in which a computer stores the bytes of a number. s390x is big-endian; x86 laptops are little-endian. | Binary files written on a laptop can be misread on Z. We use text formats (JSON, CSV) to avoid this (ADR D9). |
| **Telum** | The processor inside z16/z17 machines, which includes an on-chip AI accelerator. | It's why AI inference on Z can be fast. |
| **NNPA (Neural Network Processing Assist)** | The CPU instructions that run the Telum AI accelerator. `/proc/cpuinfo` shows `nnpa` when it's available. | llama.cpp in our image can send Granite's matrix maths to it. |
| **zDNN** | IBM's library that lets software use NNPA. `ibm-zdnn-plugin` connects it to TensorFlow; llama.cpp has a zDNN backend. | Our Granite explainer gets hardware acceleration through it. |
| **OpenBLAS / VXE** | OpenBLAS is a fast maths library; VXE are Z's vector (SIMD) instructions that process many numbers at once. | The other acceleration path for llama.cpp on Z. |
| **Snap ML** | An IBM machine-learning library tuned for IBM Z/Power, which can import XGBoost models and run them fast. | Candidate faster inference engine (M2, ADR D2). |
| **CPACF** | The cryptography accelerator built into every Z processor; it speeds up hashing and encryption. | Supports the "security on Z" story; SHA-256 in our audit chain benefits on Z. |
| **Event code `SSF2026`** | Code entered when registering on L1CC so the VM gets Datathon-sized resources. | Already done during setup. |

## 2. Linux, containers and networking

| Term | What it is | Why it matters here |
|---|---|---|
| **SSH** | Secure remote login to another computer over the network, using a key file. | The only way into the VM: `ssh -i key.pem linux1@<ip>`. |
| **SSH key pair (`.pem`)** | A private key (secret, stays on your laptop) and a public key (on the server). Possession of the private key proves who you are. | The L1CC private key downloads once and can't be retrieved again, so keep it safe. |
| **SSH tunnel / port forwarding** | `ssh -L 8000:localhost:8000 ...` makes `localhost:8000` on your laptop reach port 8000 on the VM, encrypted inside SSH. | We show the demo without opening any public port (ADR D8). |
| **Port** | A numbered "door" on a computer for a network service (SSH = 22, Jupyter = 38888, our API = 8000). | Only SSH and Jupyter are open on the VM. |
| **Firewall / iptables** | Rules that decide which ports accept outside connections. iptables is the Linux tool for them. | The L1CC VM blocks everything except SSH by default. |
| **sudo** | Run one command as the administrator (root). | Needed for firewall changes; direct root login is disabled. |
| **Container** | A packaged program plus everything it needs (Python, libraries), running isolated from the rest of the machine. | The API and the explainer each run in one, so they can't disturb each other. |
| **Container image** | The read-only template a container starts from. | Ours is built `FROM` the L1CC Jupyter image (ADR D7). |
| **Containerfile / Dockerfile** | The recipe for building an image (`FROM`, `RUN pip install`, `COPY`, `CMD`). | `containers/Containerfile`. |
| **Podman** | A tool for building and running containers (compatible with Docker, no background daemon, can run without root). | The RHEL alternative; our Ubuntu VM uses Docker. |
| **Docker** | The best-known container tool; same commands as Podman. | Our VM's container tool (Ubuntu 24.04). |
| **docker group** | Linux group whose members may run `docker` without `sudo`. | Set up with `usermod -aG docker $USER`; reconnect SSH if you get "permission denied" on the Docker socket. |
| **Host network (`--network host`)** | The container uses the VM's network directly instead of its own. | Jupyter and our two containers use it; the API binds to `127.0.0.1` so it stays private. |
| **Pod** | A Podman feature: a group of containers that share a network. | Not used: on Docker both our containers use the host network instead. |
| **Bind mount / volume** | Making a folder on the host appear inside a container (`-v host:container`). | `artifacts/` is shared by both containers and the host. |
| **`:z` volume flag** | Tells Podman to relabel the folder so SELinux (RHEL's security layer) allows the container to use it. | Only needed on RHEL/SELinux; our Ubuntu VM doesn't need it. |
| **cpuset / CPU pinning** | Limiting a container to specific CPU cores (`--cpuset-cpus 0-1`). | Keeps the slow LLM from stealing CPU from the fast decision path. |
| **cgroups** | The Linux feature that enforces container resource limits (CPU, memory). | Docker uses them for `--cpuset-cpus` and `--cpus`. |
| **seccomp** | A Linux filter on which system calls a container may use. | Some L1CC containers need `--security-opt seccomp=unconfined`. |
| **RHEL / Ubuntu** | Two Linux distributions offered on L1CC. | Decides podman vs docker and where firewall rules are saved. |
| **Jupyter Lab** | A web IDE for notebooks: code cells, outputs, charts. | Training and evidence notebooks run in the L1CC Jupyter container on port 38888. |
| **Notebook kernel** | The Python process behind a notebook. | Shut kernels down before benchmarks; they use CPU and memory. |

## 3. Python packaging

| Term | What it is | Why it matters here |
|---|---|---|
| **pip / PyPI** | Python's installer and its public package index. | Where we check s390x availability. |
| **Wheel (`.whl`)** | A pre-built package, ready to install. Its filename says which CPU it's for (e.g. `manylinux_..._s390x`). | No s390x wheel → pip tries to build from source, which often fails or takes ages. |
| **`none-any` wheel (pure Python)** | A wheel with no compiled code, so it works on any CPU. | fastapi, uvicorn, faker, pytest, onnxmltools are safe on Z. |
| **sdist (source distribution)** | Source code pip must compile itself. | cryptography/shap/pynacl only offer this on s390x, so they're risky. |
| **manylinux** | A standard that makes compiled wheels work across Linux distributions. | Look for `manylinux..._s390x` in filenames. |
| **venv / virtual environment** | An isolated Python install for one project. | The image has one at `/opt/venv`; laptops create `.venv` with `uv`. |
| **uv** | A fast Python package and environment manager. | Used to create the laptop venv with Python 3.12. |
| **Pinning** | Fixing exact versions (`xgboost==3.4.1`). | Laptop and VM must run identical versions so the parity tests mean something. |
| **src layout / editable install** | Code lives in `src/shieldz/`; `pip install -e .` makes it importable while you edit it. | Notebooks, tests and containers all import the same package. |

## 4. Machine learning

| Term | What it is | Why it matters here |
|---|---|---|
| **PaySim** | A public, synthetic (computer-generated) dataset of 6.3M mobile-money transactions, labelled fraud / not fraud. | Our training data. No real people; no age/demographic fields. |
| **Synthetic data** | Data generated by a program that looks realistic but describes no real person. | Lets us train and test without touching real personal data. |
| **Feature** | A number the model looks at, e.g. "amount ÷ balance". | We use **decision-time features only** (ADR D12). |
| **Feature engineering** | Turning raw columns into useful features. | `features/engineer.py`, shared by training and serving. |
| **Data leakage** | When training uses information that wouldn't be available at prediction time, making the model look better than it is. | PaySim's post-transaction balances leak the answer, so we drop them. |
| **Training / validation / test split** | Separate data for learning, for tuning, and for the final honest score. | Never tune on the test set. |
| **Time-based split** | Splitting by time (train on earlier days, test on later ones) instead of randomly. | Closer to reality: the model must predict the future. |
| **Class imbalance** | Fraud is rare (about 0.1% of PaySim). | Handled with `scale_pos_weight`; measured with PR-AUC, not accuracy. |
| **XGBoost** | A popular, fast algorithm that builds many small decision trees, each correcting the last ("gradient-boosted trees"). | Our fraud model. |
| **Decision tree / gradient boosting** | A tree asks yes/no questions about features; boosting adds trees one by one to fix earlier mistakes. | Why XGBoost is fast to run: just walking small trees. |
| **`hist` tree method** | XGBoost's fast training mode that groups feature values into buckets. | Fast enough to train on full PaySim on the VM. |
| **Early stopping** | Stop adding trees when the validation score stops improving. | Prevents overfitting. |
| **Overfitting** | The model memorises training data instead of learning patterns, so it does badly on new data. | Checked via the time-based holdout. |
| **Probability / risk score** | The model's output between 0 and 1. | Kept internal; never logged or returned (invariant I5). |
| **Threshold** | The cut-off that turns a score into a decision (`≥ t_block` → BLOCK). | We have two: `t_review` and `t_block`. |
| **Precision** | Of the transactions we flagged, how many were really fraud. | Low precision = annoying false alarms for elderly users. |
| **Recall** | Of all the real frauds, how many we caught. | Low recall = missed scams. |
| **False positive rate (FPR)** | Of the normal transactions, how many we wrongly flagged. | Gate: recall ≥ 0.80 at FPR ≤ 1%. |
| **PR-AUC** | Area under the precision-recall curve: one number summarising precision vs recall across all thresholds. Good for rare events. | Main model metric (gate ≥ 0.80). |
| **ROC-AUC** | Area under the true-positive vs false-positive curve. Looks optimistic when positives are rare. | Reported, but not used for the gate. |
| **Confusion matrix** | A 2×2 table: true/false positives and negatives. | In the model card. |
| **Model card** | A short document describing what a model does, its data, its metrics and its limits. | `results/MODEL_CARD.md`, honest about synthetic data. |
| **Inference** | Running a trained model on new input. | What the decision service does per request. |
| **`inplace_predict`** | XGBoost's fastest way to predict without building a DMatrix first. | Keeps single-request latency low. |
| **`nthread=1`** | Use one CPU thread for a prediction. | For one row, multi-threading costs more than it saves and causes latency spikes. |
| **SHAP** | A method that splits a model's score into contributions from each feature ("amount pushed the risk up by +2.1"). | Tells us *why* a payment looks risky. |
| **TreeSHAP / `pred_contribs`** | The exact, fast SHAP algorithm for tree models. XGBoost has it built in (`predict(..., pred_contribs=True)`). | We use this instead of the `shap` package (ADR D3). |
| **Reason code** | A fixed label for a top SHAP feature, e.g. `ACCOUNT_DRAIN`. | The only thing the LLM ever sees. |
| **Level (LOW/MEDIUM/HIGH)** | A coarse bucket for how strong a reason is. | Gives detail without revealing actual numbers. |
| **Bucketing** | Replacing exact values with ranges ("HIGH" instead of "₹48,250.37"). | Removes identifying detail. |
| **ONNX** | An open file format for trained models, so a model trained in one tool can run in another runtime. | We export to ONNX for portability; we don't serve it on Z (ADR D2). |
| **ONNX Runtime** | The main engine for running ONNX models. | No s390x build on PyPI, so we don't depend on it. |
| **onnxmltools / `onnx.checker`** | Converter from XGBoost to ONNX / validator for ONNX files. | M2 export step. |
| **Golden file / parity test** | A saved set of inputs with known-correct outputs. The test checks the code still produces exactly those outputs, here on both laptop and LinuxONE. | Catches s390x or version differences early. |
| **Property test** | A test that checks a rule holds for many generated inputs ("every output is a valid reason code"). | Used for reason codes and the guard. |

## 5. Generative AI

| Term | What it is | Why it matters here |
|---|---|---|
| **LLM (large language model)** | An AI model that generates text. | Writes the warning message. |
| **IBM Granite** | IBM's family of open LLMs. | Our explainer model, from the mandatory Lab 2. |
| **llama.cpp / llama_cpp_python** | A C++ engine for running LLMs efficiently on CPUs, and its Python binding. | How Granite runs on the VM, with zDNN/NNPA acceleration. |
| **GGUF** | The model file format used by llama.cpp. | Granite's weights are a `.gguf` file in the image. |
| **Quantization (e.g. Q4_K_M)** | Storing model weights with fewer bits (4 instead of 16) so the model is smaller and faster, with a small quality loss. | Makes Granite practical on CPU. |
| **Tokens / tokens per second** | LLMs read and write text in small pieces called tokens; speed is measured in tokens/second. | Measured in M0; tells us how long a warning takes. |
| **Prompt** | The text sent to the LLM. | Built only from a template plus enum values (invariant I2). |
| **Template** | Fixed text with slots filled from a closed set of values. | The prompt template, and the `TemplateExplainer` fallback. |
| **Closed vocabulary** | Only values from a fixed, known list are allowed. | Makes it structurally impossible for PII to enter the prompt. |
| **Allowlist vs denylist** | Allowlist = "only these things are permitted". Denylist = "these things are forbidden". | We use allowlists (guard, logging): a denylist always misses something. |
| **Guard / firewall (for prompts)** | Code that checks a prompt before it reaches the LLM and refuses anything that breaks the rules. | `explainer/guard.py`: rejects digits, unknown codes, extra text. |
| **Output guard** | Checks the LLM's answer before showing it. | Falls back to the template if the answer has numbers, links or `@`. |
| **Prompt injection** | Text crafted to trick an LLM into ignoring its instructions ("ignore previous instructions…"), e.g. in a payment memo. | Impossible here: the memo is dropped at `strip()` and never reaches the prompt. |
| **Hallucination** | An LLM stating something false with confidence. | The output guard and short, constrained prompts reduce the risk. |
| **RAG (retrieval-augmented generation)** | Giving the LLM relevant documents to read before answering. | Used in Lab 2 (BM25 over policy docs); not needed by ShieldZ. |
| **BM25** | A classic keyword-based search ranking method. | Appears in Lab 2 only. |

## 6. Privacy and security

| Term | What it is | Why it matters here |
|---|---|---|
| **PII (Personally Identifiable Information)** | Any detail that can identify a person: name, phone, account number, UPI ID, email, address. | Must never reach the LLM, logs or stored files. |
| **Canary record** | A fake PII record planted on purpose. If it shows up where it shouldn't, we've found a leak. | The core of the Leak Audit. |
| **Faker** | A Python library that generates realistic fake names, phones and addresses. | Generates the 1,000 canaries (Indian locale, seeded). |
| **Seed** | A starting number for random generation; the same seed gives the same "random" data. | Makes the Leak Audit repeatable. |
| **Leak Audit** | Our test that replays canaries through the system and scans everything for them. | The headline novelty. |
| **Sink** | Any place data ends up: log, database, file, prompt, response. | The Leak Audit scans every registered sink plus a catch-all. |
| **Variant (of a canary)** | A transformed version of a value: lower-case, digits-only, base64, hex, URL-encoded, hashed. | Leaks are often disguised; we check all the common disguises. |
| **Base64 / hex / URL-encoding** | Ways to write data as text characters. | A leaked value might be stored in one of these forms. |
| **Partial leak** | Part of a value, e.g. 6+ consecutive digits of a phone number. | Counted separately; must also be 0. |
| **Positive control** | Deliberately planting known leaks to prove the scanner catches them. | Without it, "0 leaks" might just mean the scanner is broken. |
| **False negative (of the scanner)** | A real leak the scanner fails to detect. | What the positive control guards against. |
| **Scorecard** | The Leak Audit's output: records, sinks, bytes scanned, leaks found, control result, platform. | `results/leak_scorecard_*.json/.md`, shown in the video. |
| **Tokenization (privacy sense)** | Replacing a sensitive value with a stand-in token. | Account IDs become HMAC tokens. |
| **Pseudonymization** | Replacing identifiers so data can't be linked to a person without extra information kept separately. | What HMAC tokens give us. |
| **Hash / SHA-256** | A function that turns any data into a fixed-length fingerprint; tiny input changes give a totally different fingerprint, and you can't run it backwards. | Used for the audit chain. |
| **MD5 / SHA-1** | Older hash functions. | The scanner checks for these hashes of canaries too. |
| **Dictionary attack (on a hash)** | Reversing a plain hash by hashing every possible input (e.g. every 10-digit account number) until one matches. | Why plain hashing of account numbers isn't private enough. |
| **HMAC** | A hash that also uses a secret key; without the key nobody can recompute or reverse it. | `HMAC-SHA256(pepper, account_id)` (ADR D10). |
| **Pepper** | The secret key used in our HMAC, stored outside the database and never committed. | `artifacts/keys/pepper`. |
| **Redaction** | Removing or masking sensitive parts of data. | We go further: logging uses an allowlist, so unknown fields are never written. |
| **Structured logging** | Logs written as fields (JSON) instead of free sentences. | Makes allowlisting and scanning reliable. |

## 7. Tamper-evident audit trail and cryptography

| Term | What it is | Why it matters here |
|---|---|---|
| **Audit trail / audit log** | A record of every decision, for later review by compliance or regulators. | `artifacts/runtime/audit/chain.jsonl`. |
| **Append-only** | You can only add to the end, never edit or delete. | Required for trust in the record. |
| **Hash chain** | Each entry stores the hash of the previous entry, so changing any old entry breaks every hash after it. | Makes tampering detectable (invariant I7). |
| **Tamper-evident** | You can't stop someone editing the file, but you can always tell that they did. | The honest claim we make. |
| **Canonical JSON** | JSON written in one exact way (sorted keys, no extra spaces), so the same data always gives the same bytes and the same hash. | Needed for hashes to be reproducible. |
| **Digital signature** | Proof, made with a private key and checked with a public key, that data came from the key holder and hasn't changed. | Signs audit entries or checkpoints. |
| **Public / private key** | A key pair: the private key signs (secret), the public key verifies (shareable). | Public key goes in `results/`; private key stays in `artifacts/keys/`. |
| **Ed25519** | A modern, fast, widely used signature algorithm. | Our signing algorithm. |
| **RFC 8032** | The official specification of Ed25519, including test vectors. | If we implement Ed25519 ourselves, we follow it and must pass its test vectors. |
| **Test vectors** | Official example inputs with known-correct outputs. | Proves a crypto implementation is correct. |
| **Checkpoint signing** | Signing only the latest chain hash periodically instead of every entry. Because of the chain, that one signature covers everything before it. | Fallback if signing is slow (ADR D6). |
| **Post-quantum cryptography** | Algorithms designed to stay secure even against future quantum computers. | A stretch goal. |
| **ML-DSA (Dilithium)** | A post-quantum signature algorithm, standardised by NIST as FIPS 204 (CRYSTALS-Dilithium). | The stretch-goal signature. |
| **liboqs** | Open Quantum Safe, an open-source library of post-quantum algorithms. | Must build on s390x; 90-min timebox. |

## 8. Services and performance

| Term | What it is | Why it matters here |
|---|---|---|
| **API** | A defined way for programs to talk to each other, here HTTP endpoints like `POST /v1/score`. | How a bank app would call ShieldZ. |
| **Endpoint** | One URL + method of an API. | `/v1/score`, `/v1/explanations/{id}`, `/healthz`. |
| **FastAPI** | A Python framework for building APIs, with validation built in. | Our decision service. |
| **Pydantic** | A library that defines data shapes and validates input against them. | `contracts.py`. |
| **Uvicorn / ASGI** | Uvicorn is the server that runs FastAPI apps; ASGI is the standard interface between them. | Starts the API in the container. |
| **Event loop / thread pool** | The event loop handles many network requests in one thread; CPU-heavy work goes to a pool of threads so it doesn't block the loop. | The score endpoint is a plain `def`, so FastAPI runs it in the thread pool. |
| **Synchronous / asynchronous** | Synchronous: the caller waits for the result. Asynchronous: it happens in the background. | The decision is synchronous; the explanation is asynchronous. |
| **Outbox pattern** | The main service writes "work to do" into a table, and a separate worker picks it up later. | `outbox.sqlite` → explainer worker (ADR D5). |
| **Worker / polling** | A background process that repeatedly checks for new work. | The explainer polls the outbox. |
| **SQLite / WAL mode** | SQLite is a database in a single file with no server. WAL (write-ahead logging) lets readers and a writer work at the same time. | The outbox and history store. |
| **Latency** | How long one request takes. | Target < 50 ms. |
| **p50 / p95 / p99** | Percentiles: p50 is the typical time; p99 means 99% of requests are at least this fast. | The 50 ms target is for p99, so it covers the near-worst cases. |
| **Throughput** | Requests handled per second. | Reported alongside latency. |
| **Concurrency** | How many requests are in flight at the same time. | Benchmarked at 1 and 8. |
| **Warm-up** | Requests sent before measuring, so caches and lazy loading don't distort the numbers. | 500 warm-up requests. |
| **Server-side vs client-side latency** | Time inside the service vs time seen by the caller (adds network). | We report both; the client runs on the VM to exclude internet time. |
| **Health check (`/healthz`)** | An endpoint that reports whether the service is up (plus platform and model version). | Shows `s390x` in the demo. |

## 9. Process and collaboration

| Term | What it is | Why it matters here |
|---|---|---|
| **Milestone (M0–M8)** | A chunk of work with a clear goal. | See IMPLEMENTATION_PLAN.md. |
| **Gate / checkpoint** | A list of checks that must all pass before a milestone counts as done. | Each has a local half and a LinuxONE half. |
| **Spike** | A short, time-limited experiment to answer a question ("does cryptography install on s390x?"). | M0 is mostly spikes. |
| **Timebox** | A fixed time limit; when it's up, you stop and take the fallback. | Stops us sinking hours into s390x builds. |
| **Feature freeze** | The point after which no new features are added, only fixes. | 05:30 IST, Sun 18 Oct. |
| **Cut order** | The agreed list of what to drop first if we fall behind. | IMPLEMENTATION_PLAN.md §6. |
| **Invariant** | A rule that must always stay true, whatever changes. | I1–I9 in ARCHITECTURE.md §6. |
| **ADR (Architecture Decision Record)** | A short note recording a design decision and why it was made. | DECISIONS.md. |
| **Contract (code sense)** | Agreed data shapes between parts of the system. | `contracts.py`, frozen at the M1 gate. |
| **Stub** | A temporary fake version of a component, so others can work before the real one exists. | The proof build tests the scanner against a stub service. |
| **Trunk-based development** | Everyone merges small changes into `main` frequently. | Our git model. |
| **Branch / PR / squash merge / rebase** | Branch: a separate line of work. PR: a request to merge it, with review. Squash merge: the PR becomes one commit on `main`. Rebase: replay your commits on top of the latest `main`. | See GIT_WORKFLOW.md. |
| **Conventional Commits** | A commit-message style `type(area): summary`. | Readable history. |
| **Tag** | A permanent name for a commit, e.g. `m3-gate`. | Known-good points to go back to. |
| **Deploy key** | An SSH key that gives one server read-only access to one repo. | How the VM can clone a private repo. |
| **Handoff** | Passing unfinished work to another person or agent. | progress.md + explanation.md protocol. |
| **Role** | One member's area of responsibility and the folders only they edit. | Main build, proof build, LinuxONE operator, pitch & review (plan §3). |
| **Baton (relay)** | The right to edit the main-build files. Exactly one member holds it at a time and passes it on at a handoff. | Lets the critical path continue overnight without conflicts. |
| **Critical path** | The chain of tasks where each needs the previous one, so it sets the minimum finish time. | Contracts → features → model → service → integration. |
