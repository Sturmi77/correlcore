"""FastAPI application factory."""

from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from typing import cast

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.requests import Request
from starlette.responses import Response

from app.api.v1.router import api_router
from app.core.auth_cookies import warn_if_http_staging_may_drop_cookies
from app.core.config import settings
from app.core.error_tracking import init_error_tracking
from app.core.logging import setup_logging
from app.core.rate_limit import limiter
from app.core.request_id import RequestIDMiddleware
from app.services.health_service import check_liveness


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan — startup and shutdown hooks."""
    setup_logging()
    init_error_tracking(settings)
    warn_if_http_staging_may_drop_cookies()
    # Connection pools are opened lazily by their dependencies. Keep the
    # lifespan hook focused on process-wide setup until a measured startup
    # warmup or explicit shutdown hook is required.
    yield


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="CorrelCore API",
        description="Privacy-first Mood & Habit Tracker API",
        version="0.0.1",
        docs_url="/api/docs" if settings.DEBUG else None,
        redoc_url="/api/redoc" if settings.DEBUG else None,
        openapi_url="/api/openapi.json" if settings.DEBUG else None,
        lifespan=lifespan,
    )

    # ── Rate limiter state ──────────────────────────────────────────────────
    app.state.limiter = limiter
    app.add_exception_handler(
        RateLimitExceeded,
        cast(Callable[[Request, Exception], Response], _rate_limit_exceeded_handler),
    )

    # ── Middleware (outermost first) ────────────────────────────────────────
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(
        CORSMiddleware,
        # Include Capacitor WebView origin (https://localhost) automatically.
        allow_origins=settings.cors_allow_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Accept", "X-Request-ID"],
        expose_headers=["X-Request-ID"],
    )

    # ── Routers ────────────────────────────────────────────────────────────
    app.include_router(api_router, prefix="/api/v1")

    # ── Root health shortcuts (Docker HEALTHCHECK) ─────────────────────────
    @app.get("/health/live", include_in_schema=False)
    async def root_live() -> JSONResponse:
        return JSONResponse(check_liveness())

    @app.get("/health", include_in_schema=False)
    async def root_health() -> JSONResponse:
        return JSONResponse(check_liveness())

    return app


app = create_app()
