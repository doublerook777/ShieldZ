"""FastAPI app. Run with: uvicorn shieldz.service.app:create_app --factory --no-access-log

Handlers are plain `def`, so FastAPI runs them in its thread pool and CPU-bound scoring does not
block the event loop. Access logs stay off (they would log paths and clients, I4); application
logging goes through `privacy.redact_log` only.
"""

from __future__ import annotations

import importlib.util
import json
import platform
from contextlib import asynccontextmanager
from pathlib import Path as FsPath

from fastapi import FastAPI, Path, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from shieldz import config
from shieldz.audit.verify import verify_audit_trail
from shieldz.contracts import Decision, Explanation, PaymentRequest
from shieldz.privacy.redact_log import log_event, setup_logging
from shieldz.service.pipeline import Pipeline

DECISION_ID = r"^[0-9a-f]{32}$"
STATIC_DIR = FsPath(__file__).parent / "static"
# Aggregate scorecard fields only. `findings` is left out so a failing run can't echo scanned text.
SCORECARD_FIELDS = (
    "timestamp", "environment", "platform", "git_sha", "records_replayed", "sinks_scanned",
    "total_bytes_scanned", "bytes_per_sink", "positive_control_planted", "positive_control_found",
    "negative_control_decoys", "negative_control_hits", "leaks_exact", "leaks_variant",
    "leaks_partial", "status",
)  # fmt: skip


class DemoFiles(StaticFiles):
    """The demo page is edited often; browsers must ask again instead of reusing an old copy."""

    async def get_response(self, path, scope):
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = "no-cache"
        return response


def create_app(pipeline: Pipeline | None = None) -> FastAPI:
    owns_pipeline = pipeline is None

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if owns_pipeline:
            setup_logging()
            app.state.pipeline = Pipeline.from_env()
        else:
            app.state.pipeline = pipeline
        p: Pipeline = app.state.pipeline
        p.start()
        if p.signer is not None:  # the pure-Python fallback signer stalls the api for ~250 ms
            fast = importlib.util.find_spec("cryptography") is not None
            log_event("signer_backend", status="cryptography" if fast else "pure-python")
        log_event("startup", engine=p.engine.name, model_version=p.engine.version)
        yield
        p.close()

    app = FastAPI(title="ShieldZ", lifespan=lifespan, docs_url=None, redoc_url=None)

    @app.exception_handler(RequestValidationError)
    def invalid_request(_: Request, exc: RequestValidationError) -> JSONResponse:
        """Field path and error type only. The default handler echoes the offending value (PII)."""
        detail = [{"loc": list(e["loc"]), "type": e["type"]} for e in exc.errors()]
        return JSONResponse(status_code=422, content={"detail": detail})

    @app.post("/v1/score", response_model=Decision)
    def score(request: PaymentRequest, raw: Request):
        pipeline: Pipeline = raw.app.state.pipeline
        try:
            return pipeline.handle(request)
        except Exception as exc:  # no traceback to stdout: it could carry request values
            log_event("error", error_type=type(exc).__name__)
            return JSONResponse(status_code=500, content={"detail": "internal error"})

    @app.get("/v1/explanations/{decision_id}", response_model=Explanation)
    def explanation(raw: Request, decision_id: str = Path(pattern=DECISION_ID)):
        found = raw.app.state.pipeline.outbox.get_explanation(decision_id)
        if found is None:
            return JSONResponse(status_code=404, content={"detail": "not ready"})
        return found

    @app.get("/healthz")
    def healthz(raw: Request) -> dict:
        engine = raw.app.state.pipeline.engine
        return {
            "status": "ok",
            "platform": platform.machine(),
            "engine": engine.name,
            "model_version": engine.version,
        }

    @app.get("/v1/audit/verify")
    def audit_verify() -> dict:
        """Re-verify the whole chain and its signed checkpoints, as `make verify` does."""
        ok, message, seq = verify_audit_trail(
            config.audit_chain_file(), config.audit_checkpoints_file(), config.audit_public_key()
        )
        return {"ok": ok, "message": message, "failure_seq": seq}

    @app.get("/v1/leak-scorecard")
    def leak_scorecard():
        """Newest committed Leak Audit result: LinuxONE's if there is one, else the local run."""
        for env in ("linuxone", "local"):
            path = config.results_dir() / f"leak_scorecard_{env}.json"
            if path.exists():
                data = json.loads(path.read_text())
                return {k: data[k] for k in SCORECARD_FIELDS if k in data}
        return JSONResponse(status_code=404, content={"detail": "no scorecard yet"})

    if STATIC_DIR.is_dir():  # the demo page (Member 4); mounted last so it can't shadow the API
        app.mount("/", DemoFiles(directory=STATIC_DIR, html=True), name="static")

    return app
