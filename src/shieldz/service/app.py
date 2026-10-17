"""FastAPI app. Run with: uvicorn shieldz.service.app:create_app --factory --no-access-log

Handlers are plain `def`, so FastAPI runs them in its thread pool and CPU-bound scoring does not
block the event loop. Access logs stay off (they would log paths and clients, I4); application
logging goes through `privacy.redact_log` only.
"""

from __future__ import annotations

import platform
from contextlib import asynccontextmanager

from fastapi import FastAPI, Path, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from shieldz.config import runtime_dir
from shieldz.contracts import Decision, Explanation, PaymentRequest
from shieldz.privacy.redact_log import log_event, setup_logging
from shieldz.service.pipeline import Pipeline

DECISION_ID = r"^[0-9a-f]{32}$"


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
        log_event("startup", engine=p.engine.name, model_version=p.engine.version)
        yield
        if owns_pipeline:
            p.history.save(runtime_dir() / "history.sqlite")

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

    return app
