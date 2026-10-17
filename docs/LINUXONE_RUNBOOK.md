# ShieldZ — LinuxONE Runbook

How to work with the LinuxONE Community Cloud VM. The VM and the Jupyter Lab ML container are **already set up**: the team followed the **Ubuntu 24.04 + Docker** path of the jupyter-lab-ml README (image **Ubuntu 24.04-Datathon**, **Docker 29.8.0**). This runbook starts from there. Default operator: **Member 3**, but any member can follow it.

Sources:
- the [Datathon setup guide](https://ibmz-datathon-guide.vercel.app/);
- [deploy-virtual-server.md](https://github.com/linuxone-community-cloud/technical-resources/blob/master/faststart/deploy-virtual-server.md);
- [jupyter-lab-ml](https://github.com/linuxone-community-cloud/jupyter-lab-ml): README (the setup the team used), README_RHEL, `packages.txt`, the Lab notebooks;
- [LinuxONE Fast Start](https://community.ibm.com/zsystems/l1cc/faststart/).

Fill in the blanks in `progress.md` → "LinuxONE facts" during M0, then use them here.

---

## 1. Facts from the official guides

| Item | Value |
|---|---|
| Login | `ssh -i <key>.pem linux1@<vm-ip>`. Key only; password login and `root` login are disabled; `sudo` works. The official guide shows `ssh –i` with an en dash; type a normal hyphen `-i` |
| Key permissions | `chmod 600 <key>.pem` |
| Firewall | iptables; **only SSH is open by default**. Jupyter's 38888 was opened during setup |
| Persist firewall rules | **Ubuntu:** `sudo bash -c "iptables-save > /etc/iptables/rules.v4"`. The jupyter-lab-ml README shows the RHEL path `/etc/sysconfig/iptables.save`, which is wrong for Ubuntu. (RHEL `/etc/sysconfig/iptables.save`, SLES `/etc/linuxone/iptables.save`.) If you switch to ufw, delete the saved file |
| Container tool | **Docker** (installed with get.docker.com). `linux1` is in the `docker` group, so no `sudo` is needed. If you get "permission denied … docker.sock", reconnect SSH or run `exec bash` |
| Jupyter image | `registry.linuxone.cloud.marist.edu/l1cc/jupyterlab-image-s390x:latest`, container name `notebook`, `--network host`, port **38888** |
| Jupyter URL / token | `http://<vm-ip>:38888`, default token `Your_Token1`. The VM has a public IP, so consider changing the token |
| Shared folder | VM `/home/linux1/shared` ↔ container `/home/ibm-user/shared` (container user uid 1000) |
| Python in the image | 3.12, venv at `/opt/venv` |
| Preinstalled ML stack | xgboost 3.4.1, numpy 2.0.2, pandas 3.0.6, scikit-learn 1.9.0, onnx 1.22.0, skl2onnx, tf2onnx, torch 2.11 (cpu) + torch_nnpa, tensorflow 2.18 + ibm-zdnn-plugin, transformers 5.19, llama_cpp_python 0.3.36 (built with zDNN/NNPA + OpenBLAS), httpx 0.28.1, huggingface_hub |
| Not in the image | onnxruntime, shap, fastapi, uvicorn, faker, cryptography, pytest, pyarrow |
| Demo notebooks in the image | (1) `Fraud_LSTM_Keras_TF.ipynb`: LSTM fraud model, ONNX via tf2onnx, NNPA via ibm-zdnn-plugin · (2) `Churn_Scikit_PyTorch.ipynb`: random forest, PMML export · (3) `Digit_Class_TensorFlow.ipynb`: MNIST, ONNX export · (4) `Loan_Approval_Demo.ipynb`: XGBoost + **IBM Granite via llama.cpp** + BM25 RAG, helper code in `loan_demo/` |
| Mandatory labs (guidebook) | "Predictive AI hybrid (multi-model)" and "Predictive + Generative AI". Notebooks (1)/(2) and (4) cover these |
| Upload limits | Jupyter web upload ≤ 200 MB per file; use `scp` for anything bigger |
| Backups | **None.** Anything that matters must be in git or copied back to a laptop |

---

## 2. One-time setup on the VM (M0)

```bash
ssh -i ~/.ssh/l1cc.pem linux1@<vm-ip>

# Clone into the shared folder so Jupyter sees the same files
cd ~/shared
# The repo is PRIVATE for now (C-002), so the VM needs a read-only deploy key:
ssh-keygen -t ed25519 -f ~/.ssh/shieldz_deploy -N ""
cat ~/.ssh/shieldz_deploy.pub
#   → GitHub repo → Settings → Deploy keys → Add deploy key (paste, leave "Allow write access" OFF)
cat >> ~/.ssh/config <<'EOF'
Host github.com
  IdentityFile ~/.ssh/shieldz_deploy
  IdentitiesOnly yes
EOF
git clone git@github.com:doublerook777/ShieldZ.git
# Once the repo is public, plain `git clone https://github.com/doublerook777/ShieldZ.git` also works.
cd ShieldZ && mkdir -p data artifacts results && chmod a+w data artifacts results

# Record facts for progress.md
uname -m; head -2 /etc/os-release; nproc; free -h; df -h ~
grep -o nnpa /proc/cpuinfo | head -1          # prints "nnpa" if the AI accelerator facility is visible
docker --version
docker exec notebook /opt/venv/bin/python --version
docker exec notebook /opt/venv/bin/python -c "import xgboost, numpy, pandas, llama_cpp; print(xgboost.__version__, numpy.__version__, pandas.__version__)"
```

Copy PaySim from your laptop (the file is bigger than Jupyter's 200 MB upload limit):
```bash
# on the laptop
scp -i ~/.ssh/l1cc.pem paysim1.zip linux1@<vm-ip>:~/shared/ShieldZ/data/
# on the VM (unzip with the container's Python, so nothing needs installing)
docker exec notebook /opt/venv/bin/python -m zipfile -e \
  /home/ibm-user/shared/ShieldZ/data/paysim1.zip /home/ibm-user/shared/ShieldZ/data/
```

Find the Lab 2 Granite model (M0 task 3). Look only; don't copy their code:
```bash
docker exec notebook bash -lc 'find / -name "*.gguf" 2>/dev/null; /opt/venv/bin/python -c "import loan_demo, os; print(os.path.dirname(loan_demo.__file__))"'
```

---

## 3. Daily sync (every gate)

```bash
# laptop: merge to main, then on the VM:
cd ~/shared/ShieldZ && git switch main && git pull --ff-only
# to gate a branch before merging:
git fetch && git switch --detach origin/m3/service-outbox
```
The VM is **pull-only**. If something must change, change it on a laptop, push, then pull.

---

## 4. Running the gate on the VM

```bash
cd ~/shared/ShieldZ
make z-build            # docker build -t shieldz:latest -f containers/Containerfile .
make z-gate             # runs inside the shieldz image: pytest (all markers) + scripts/z_doctor.py + milestone checks
```
`make z-gate` writes its output to `results/` and prints a summary to paste into `progress.md`.

Copy results back to a laptop and commit them there:
```bash
# laptop
scp -i ~/.ssh/l1cc.pem -r linux1@<vm-ip>:~/shared/ShieldZ/results/ ./
git switch -c docs/m3-results && git add results && git commit -m "docs(progress): M3 results from LinuxONE"
```

---

## 5. Running the system (M3+)

`make z-up` wraps these commands. Docker has no pods, so both containers use the host network (ADR D14):

```bash
docker build -t shieldz:latest -f containers/Containerfile .
N=$(nproc)                                      # never ask for cores that don't exist
if   [ "$N" -ge 4 ]; then API_CPUS=0-1; EXP_CPUS=2-$((N-1))
elif [ "$N" -eq 3 ]; then API_CPUS=0;   EXP_CPUS=1-2
elif [ "$N" -eq 2 ]; then API_CPUS=0;   EXP_CPUS=1
else echo "1 vCPU: drop --cpuset-cpus and give the explainer --cpus 0.5"; fi
docker run -d --name shieldz-api       --network host --cpuset-cpus "$API_CPUS" \
  -v ~/shared/ShieldZ/artifacts:/app/artifacts shieldz:latest api        # binds 127.0.0.1:8000 only
docker run -d --name shieldz-explainer --network host --cpuset-cpus "$EXP_CPUS" \
  -v ~/shared/ShieldZ/artifacts:/app/artifacts shieldz:latest explainer
docker ps; docker stats --no-stream
curl -s localhost:8000/healthz
```
- `make z-up` computes the core split from `nproc` as above, so it never asks for cores the VM doesn't have. Leave the `notebook` container unpinned, but shut down its kernels during benchmarks.
- The Granite weights are **inside the L1CC base image** (`/home/ibm-user/granite-4.0-h-350m-base-be.f16.gguf`; they are not on the VM host), so `make z-up` just sets `SHIELDZ_EXPLAINER=granite` and the explainer finds them. To use other weights: `make z-up GRANITE_GGUF=/host/path/file.gguf` (mounted read-only at `/models/granite.gguf`). Check: `docker logs shieldz-explainer` shows `worker_start`, then `explained ... source=granite` after a BLOCK (about 16 s later). The explainer falls back to the template if `llama_cpp` or the file is missing, so always check `source`.
- If a container won't start with seccomp errors, add `--security-opt seccomp=unconfined` (the official README mentions this).
- Stop: `docker rm -f shieldz-api shieldz-explainer` (`make z-down`).
- Because of `--network host`, the API must bind `127.0.0.1`, **not** `0.0.0.0`. Otherwise it would be reachable from the internet if anyone opens port 8000 in the firewall.

Reach the API and demo UI from a laptop **through an SSH tunnel** (no public port, ADR D8):
```bash
ssh -i ~/.ssh/l1cc.pem -N -L 8000:localhost:8000 linux1@<vm-ip>
# then open http://localhost:8000/ in the laptop browser
```

Latency benchmark (run **on the VM** so internet latency isn't measured). The load client runs in the `notebook` container so it doesn't share the api's pinned cores:
```bash
make bench TAG=<tag>        # results/latency_<tag>.json; exit code 1 if p99 >= 50 ms or an outbox row is missing
```
The api runs one process by default. `docker run ... -e SHIELDZ_WORKERS=2 ...` runs two (shared SQLite history/outbox keep them consistent). Try it only if p99 at concurrency 8 is too high. Do **not** use `uvicorn --workers` (it adds ~40 ms per keep-alive request); `shieldz.service.serve` is the supported launcher.
Before benchmarking, shut down idle Jupyter kernels (Jupyter → Kernel → Shut Down All Kernels).

---

## 6. Using Jupyter with the repo

The repo is visible in Jupyter at `shared/ShieldZ/`. Notebooks live in `notebooks/` and start with:
```python
import sys, platform; sys.path.insert(0, "/home/ibm-user/shared/ShieldZ/src")
print(platform.machine())          # s390x: keep this output as evidence
import shieldz
```
Notebooks only orchestrate and display (ADR D11). Keep the outputs of the training notebook on LinuxONE: they are **evidence for the video**. Clear outputs in exploration notebooks before committing.

Packages missing from the Jupyter container (e.g. faker for a notebook) can be installed with `!{sys.executable} -m pip install faker`. They disappear if the container is re-created. The service image installs its own extras from `requirements/z-extra.txt`.

---

## 7. Troubleshooting (official FAQ plus our own notes)

| Symptom | Fix |
|---|---|
| `permission denied … /var/run/docker.sock` | `exec bash` or reconnect SSH (docker group membership needs a new session) |
| Out of memory during training | `free -h`; `docker stats`; restart the kernel (Kernel → Restart Kernel and Clear Outputs); free page cache: `sudo sync && echo 3 \| sudo tee /proc/sys/vm/drop_caches`; load PaySim with `usecols` + small dtypes |
| Disk full | `df -h`; `docker image prune`; delete old `artifacts/runtime` runs. **Don't** run the FAQ's `docker rmi $(docker images -qa)` blindly: it also deletes the Jupyter image our build depends on |
| Jupyter container broken | `docker logs notebook`; `docker rm -f notebook`; re-run the original `docker run` from the README (the `shared` folder survives) |
| Permission denied in `shared/` from Jupyter | `sudo chown -R 1000:1000 ~/shared/ShieldZ` (the container user is uid 1000) and `sudo chmod -R a+w ~/shared/ShieldZ/{data,artifacts,results}` |
| VM doesn't answer ping/SSH | L1CC dashboard → Manage Instances → **Stop**, wait for SHUTOFF, then **Start** |
| `pip install` builds from source and fails | The package has no s390x wheel. Check [DECISIONS.md](DECISIONS.md) for the fallback; don't spend more than the timebox |
| Model loads but predictions differ from laptop | Check that the model was saved as JSON (not pickle) and that the golden parity test passes; check numpy/xgboost versions match `requirements/z-preinstalled.txt` |
