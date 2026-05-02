"""AutoDS API — FastAPI entry point."""
from __future__ import annotations

import logging
import time
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from api.config import get_settings
from api.logging_setup import configure_logging, setup_request_logging

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

settings = get_settings()
configure_logging()

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="AutoDS API",
    version="1.0.0",
    description="Backend API for the AutoDS autonomous data science platform.",
)

_start_time = time.time()

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_origin_regex=settings.ALLOWED_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Request body size limit (250 MB)
# Starlette ContentSizeLimitMiddleware is the cleanest in-process option.
# Alternatively pass --limit-concurrency / --limit-max-requests to uvicorn,
# or set client_max_body_size in a reverse proxy (nginx/Render).
# ---------------------------------------------------------------------------

class _BodySizeLimitMiddleware(BaseHTTPMiddleware):
    """Reject requests whose Content-Length exceeds MAX_UPLOAD_MB."""

    async def dispatch(self, request: Request, call_next):
        max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > max_bytes:
            return JSONResponse(
                status_code=413,
                content={"detail": f"Request body exceeds {settings.MAX_UPLOAD_MB} MB limit"},
            )
        return await call_next(request)


app.add_middleware(_BodySizeLimitMiddleware)
setup_request_logging(app)

# ---------------------------------------------------------------------------
# Centralised exception handler
# ---------------------------------------------------------------------------

# Exception → HTTP status mapping (adapted to actual classes in core/exceptions.py)
# Note: AutoDSError is the base class (not AutoDSException).
_EXC_TO_STATUS: dict[type, int] = {}

try:
    from core.exceptions import (  # type: ignore[import]
        AutoDSError,
        # 400 — bad input / data problems
        DataLoadError,
        DataQualityError,
        DomainDetectionError,
        EdgeCaseError,
        EmptyDataError,
        EncodingDetectionError,
        ExtremeImbalanceError,
        InsufficientDataError,
        InvalidDomainError,
        LLMParsingError,
        SchemaValidationError,
        SingleClassError,
        UnsupportedFormatError,
        # 404 — not found
        ModelNotFoundError,
        SessionNotFoundError,
        ToolNotFoundError,
        # 422 — semantic validation (edge cases)
        DataLeakageDetected,
        # 429 — rate limit
        LLMRateLimitError,
        # 500 — internal errors
        AgentError,
        FeatureCreationError,
        ModelTrainingError,
        OrchestratorError,
        PredictionError,
        ReportGenerationError,
        SessionCorruptedError,
        ToolExecutionError,
        # 502 — upstream failures
        APIConnectionError,
        CloudStorageError,
        DatabaseConnectionError,
        LLMAPIError,
    )

    _EXC_TO_STATUS = {
        DataLoadError: 400,
        DataQualityError: 400,
        DomainDetectionError: 400,
        EdgeCaseError: 422,
        EmptyDataError: 400,
        EncodingDetectionError: 400,
        ExtremeImbalanceError: 400,
        InsufficientDataError: 400,
        InvalidDomainError: 400,
        LLMParsingError: 400,
        SchemaValidationError: 400,
        SingleClassError: 400,
        UnsupportedFormatError: 400,
        DataLeakageDetected: 422,
        ModelNotFoundError: 404,
        SessionNotFoundError: 404,
        ToolNotFoundError: 404,
        LLMRateLimitError: 429,
        AgentError: 500,
        FeatureCreationError: 500,
        ModelTrainingError: 500,
        OrchestratorError: 500,
        PredictionError: 500,
        ReportGenerationError: 500,
        SessionCorruptedError: 500,
        ToolExecutionError: 500,
        APIConnectionError: 502,
        CloudStorageError: 502,
        DatabaseConnectionError: 502,
        LLMAPIError: 502,
    }

    @app.exception_handler(AutoDSError)
    async def autods_exception_handler(request: Request, exc: AutoDSError) -> JSONResponse:
        # 1. Check the explicit type-to-status map first.
        status_code = None
        for exc_type, code in _EXC_TO_STATUS.items():
            if isinstance(exc, exc_type):
                status_code = code
                break

        # 2. Fall back to message-based routing for AutoDSError instances that
        #    use descriptive messages as stand-ins for missing exception subclasses.
        #    TODO: remove this block once ResourceNotFoundError and AuthorizationError
        #    are added to core/exceptions.py and state_service.py is updated.
        if status_code is None:
            msg = str(exc).lower()
            if "not found" in msg:
                status_code = 404
            elif "access denied" in msg:
                status_code = 403
            else:
                status_code = 400

        logger.warning("AutoDSError [%s] %s: %s", status_code, type(exc).__name__, exc)
        return JSONResponse(
            status_code=status_code,
            content={"detail": str(exc), "error_type": type(exc).__name__},
        )

    logger.info("core.exceptions loaded — %d exception mappings registered", len(_EXC_TO_STATUS))

except ImportError as _e:
    logger.warning("core.exceptions not importable (%s); generic error handling only", _e)

# ---------------------------------------------------------------------------
# Mount existing serving/api.py as sub-router
# ---------------------------------------------------------------------------

try:
    from serving.api import app as serving_app  # type: ignore[import]

    app.mount("/serving", serving_app)
    logger.info("serving/api.py mounted at /serving")
except ImportError as _e:
    logger.warning("serving/api.py not available; /serving disabled (%s)", _e)

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/health", tags=["meta"])
async def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "version": "1.0.0",
        "uptime_seconds": int(time.time() - _start_time),
    }


@app.get("/", tags=["meta"])
async def root() -> dict[str, str]:
    return {"name": "AutoDS API", "docs": "/docs"}


# ---------------------------------------------------------------------------
# Routers
#
# API versioning convention:
#   All business-logic routes live under /v1.  Infrastructure endpoints
#   (/health, /, /serving/*) stay at the root and are never versioned.
#   When a breaking change requires /v2, create a second APIRouter with
#   prefix="/v2" and include it alongside v1_router below.
# ---------------------------------------------------------------------------
from fastapi import APIRouter  # noqa: E402 — must follow app creation
from api.routes import auth, chat, configure, download, eda, explainability, feature_engineering, jobs, meta, modeling, predict, projects, upload  # noqa: E402

v1_router = APIRouter(prefix="/v1")

v1_router.include_router(auth.router,                prefix="/auth",      tags=["auth"])
v1_router.include_router(projects.router,            prefix="/projects",  tags=["projects"])
v1_router.include_router(upload.router,              prefix="/upload",    tags=["upload"])
v1_router.include_router(configure.router,           prefix="/configure", tags=["configure"])
v1_router.include_router(eda.router,                 prefix="/eda",       tags=["eda"])
v1_router.include_router(feature_engineering.router, prefix="/fe",        tags=["feature-engineering"])
v1_router.include_router(modeling.router,            prefix="/modeling",  tags=["modeling"])
v1_router.include_router(explainability.router,      prefix="/explain",   tags=["explainability"])
v1_router.include_router(predict.router,             prefix="/predict",   tags=["predict"])
v1_router.include_router(chat.router,                prefix="/chat",      tags=["chat"])
v1_router.include_router(download.router,            prefix="/download",  tags=["download"])
v1_router.include_router(jobs.router,                prefix="/jobs",      tags=["jobs"])
v1_router.include_router(meta.router,                prefix="/meta",      tags=["meta"])

app.include_router(v1_router)
