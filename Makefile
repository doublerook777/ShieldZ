# ShieldZ — see docs/LINUXONE_RUNBOOK.md for the z-* targets (they run on the VM only).
.PHONY: test lint fmt leak-audit doctor z-doctor z-build z-gate z-up z-down bench verify

PY ?= .venv/bin/python
IMAGE ?= shieldz:latest
# Granite weights: the L1CC base image already contains /home/ibm-user/granite-4.0-h-350m-base-be.f16.gguf,
# so the explainer finds them without a mount. Set GRANITE_GGUF to a host file to use other weights.
GRANITE_GGUF ?=
# Explanation mode: granite (default) or template (no LLM loaded: instant, reviewed texts only)
EXPLAINER ?= granite
# Decision engine in the api container: xgboost needs artifacts/model/ (model.json, thresholds.json)
ENGINE ?= xgboost
# Cores for the benchmark client: everything except the api's core 0 (nproc = 3 on our VM)
BENCH_CPUS ?= 1-2
# Path of the repo as the Jupyter container sees it
JUPYTER_REPO ?= /home/jovyan/shared/ShieldZ

test:
	$(PY) -m pytest -m "not z and not llm"

lint:
	$(PY) -m ruff check .
	$(PY) -m ruff format --check .

fmt:
	$(PY) -m ruff format .
	$(PY) -m ruff check --fix .

doctor:
	$(PY) scripts/z_doctor.py --local

leak-audit:
	$(PY) -m shieldz.leak_audit --env local

# --- VM only -----------------------------------------------------------------

# M0: check the Jupyter container's environment (no image needed yet)
z-doctor:
	docker exec notebook /opt/venv/bin/python $(JUPYTER_REPO)/scripts/z_doctor.py

z-build:
	docker build -t $(IMAGE) -f containers/Containerfile .

z-gate: z-build
	docker run --rm -v $(CURDIR)/artifacts:/app/artifacts -v $(CURDIR)/results:/app/results \
	  $(IMAGE) bash -c "python scripts/z_doctor.py && python -m pytest"

# Core split is computed from nproc so we never ask for cores that don't exist (runbook §5)
z-up: z-build
	@N=$$(nproc); \
	if   [ $$N -ge 4 ]; then API="--cpuset-cpus 0-1"; EXP="--cpuset-cpus 2-$$((N-1))"; \
	elif [ $$N -eq 3 ]; then API="--cpuset-cpus 0";   EXP="--cpuset-cpus 1-2"; \
	elif [ $$N -eq 2 ]; then API="--cpuset-cpus 0";   EXP="--cpuset-cpus 1"; \
	else API=""; EXP="--cpus 0.5"; fi; \
	docker rm -f shieldz-api shieldz-explainer >/dev/null 2>&1 || true; \
	docker run -d --name shieldz-api --network host $$API \
	  -e SHIELDZ_ENGINE=$(ENGINE) \
	  -v $(CURDIR)/artifacts:/app/artifacts -v $(CURDIR)/results:/app/results:ro $(IMAGE) api; \
	LLM="-e SHIELDZ_EXPLAINER=$(EXPLAINER)"; \
	if [ "$(EXPLAINER)" = granite ] && [ -n "$(GRANITE_GGUF)" ]; then \
	  LLM="$$LLM -v $(GRANITE_GGUF):/models/granite.gguf:ro -e SHIELDZ_GRANITE_PATH=/models/granite.gguf"; fi; \
	docker run -d --name shieldz-explainer --network host $$EXP $$LLM \
	  -v $(CURDIR)/artifacts:/app/artifacts $(IMAGE) explainer; \
	docker ps --filter name=shieldz; \
	sleep 3; curl -s localhost:8000/healthz; echo

z-down:
	docker rm -f shieldz-api shieldz-explainer

# The load client runs in the notebook container, not in shieldz-api, so it doesn't compete for the
# api's pinned cores. Usage: make bench TAG=stub_w1   (SHIELDZ_WORKERS is set when starting the api)
bench:
	docker run --rm --network host --cpuset-cpus $(BENCH_CPUS) \
	  -v $(CURDIR)/artifacts:/app/artifacts -v $(CURDIR)/results:/app/results \
	  $(IMAGE) bash -c "python scripts/bench_latency.py \
	    --n 5000 --warmup 500 --concurrency 1 8 --cpus $(BENCH_CPUS) \
	    --outbox /app/artifacts/runtime/outbox.sqlite \
	    --out /app/results/latency_$(TAG).json"

verify:
	$(PY) -m shieldz.audit.verify artifacts/runtime/audit/chain.jsonl \
	  --checkpoints artifacts/runtime/audit/checkpoints.jsonl --pubkey artifacts/keys/audit_pubkey.pem
