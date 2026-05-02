"""Logging configuration and request-logging middleware for the AutoDS API."""
from __future__ import annotations

import logging
import time
from typing import Callable

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from api.config import get_settings


def configure_logging() -> None:
    """Configure root Python logging.

    Prefers logging_audit.structured_logger if available; falls back to
    stdlib basicConfig so the API works without the full backend installed.
    """
    settings = get_settings()
    try:
        from logging_audit.structured_logger import configure_logging as _configure  # type: ignore[import]

        _configure(level=settings.LOG_LEVEL)
    except ImportError:
        logging.basicConfig(
            level=settings.LOG_LEVEL,
            format="%(asctime)s %(levelname)s %(name)s — %(message)s",
        )


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log every HTTP request with method, path, status code, and duration."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start = time.perf_counter()
        response: Response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000

        logger = logging.getLogger("api.request")
        logger.info(
            "%s %s → %s (%.1f ms)",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        return response


def setup_request_logging(app: FastAPI) -> None:
    """Attach RequestLoggingMiddleware to *app*."""
    app.add_middleware(RequestLoggingMiddleware)
