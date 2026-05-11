"""Structured JSON logging for CorrelCore API.

Every log record emits valid JSON with a fixed set of fields.
Sensitive user data (mood values, symptoms, notes) must never appear in logs —
enforced by convention and reviewed in the DSGVO checkpoint for M1.

Usage
-----
Call ``setup_logging()`` once at application startup (in lifespan).
Then use the standard ``logging`` module everywhere::

    import logging
    logger = logging.getLogger(__name__)
    logger.info("something happened")

Request-scoped fields (request_id, method, path, status_code, duration_ms)
are injected automatically by the RequestIDMiddleware via contextvars.
"""

from __future__ import annotations

import json
import logging
import sys
import traceback
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

from app.core.config import settings

# ---------------------------------------------------------------------------
# Context variables — set per-request by RequestIDMiddleware
# ---------------------------------------------------------------------------
_ctx_request_id: ContextVar[str] = ContextVar("request_id", default="-")
_ctx_method: ContextVar[str] = ContextVar("method", default="-")
_ctx_path: ContextVar[str] = ContextVar("path", default="-")
_ctx_status_code: ContextVar[int] = ContextVar("status_code", default=0)
_ctx_duration_ms: ContextVar[float] = ContextVar("duration_ms", default=0.0)


def get_request_id() -> str:
    return _ctx_request_id.get()


def set_request_context(
    *,
    request_id: str,
    method: str = "-",
    path: str = "-",
    status_code: int = 0,
    duration_ms: float = 0.0,
) -> None:
    _ctx_request_id.set(request_id)
    _ctx_method.set(method)
    _ctx_path.set(path)
    _ctx_status_code.set(status_code)
    _ctx_duration_ms.set(duration_ms)


# ---------------------------------------------------------------------------
# JSON formatter
# ---------------------------------------------------------------------------


class _JsonFormatter(logging.Formatter):
    """Formats log records as single-line JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "service": "correlcore-api",
            "environment": settings.APP_ENV,
            "logger": record.name,
            "request_id": _ctx_request_id.get(),
            "method": _ctx_method.get(),
            "path": _ctx_path.get(),
            "status_code": _ctx_status_code.get() or None,
            "duration_ms": _ctx_duration_ms.get() or None,
            "message": record.getMessage(),
        }

        # Remove None values to keep logs compact
        entry = {k: v for k, v in entry.items() if v is not None}

        # Attach exception info — stacktrace only, never user data
        if record.exc_info:
            entry["exc_info"] = traceback.format_exception(*record.exc_info)

        return json.dumps(entry, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------


def setup_logging() -> None:
    """Configure root logger with JSON output. Call once at app startup."""
    level = logging.DEBUG if settings.DEBUG else logging.INFO

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_JsonFormatter())

    root = logging.getLogger()
    root.setLevel(level)
    # Remove any existing handlers (uvicorn adds its own)
    root.handlers.clear()
    root.addHandler(handler)

    # Quiet noisy third-party loggers in production
    if not settings.DEBUG:
        logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

    logging.getLogger(__name__).info(
        "Logging initialised",
        extra={"environment": settings.APP_ENV},
    )
