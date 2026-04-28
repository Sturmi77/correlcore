"""FastAPI application factory."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan — startup and shutdown hooks."""
    # TODO M0: initialise DB connection pool
    # TODO M0: initialise Redis connection
    yield
    # TODO M0: close DB pool
    # TODO M0: close Redis pool


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="MoodSync API",
        description="Privacy-first Mood & Habit Tracker API",
        version="0.0.1",
        docs_url="/api/docs" if settings.DEBUG else None,
        redoc_url="/api/redoc" if settings.DEBUG else None,
        openapi_url="/api/openapi.json" if settings.DEBUG else None,
        lifespan=lifespan,
    )

    # CORS — only allow frontend origin in production
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Accept", "X-Request-ID"],
    )

    # Mount versioned API router
    app.include_router(api_router, prefix="/api/v1")

    @app.get("/health", include_in_schema=False)
    async def health() -> JSONResponse:
        """Health check endpoint — used by Docker healthcheck."""
        return JSONResponse({"status": "ok", "version": "0.0.1"})

    return app


app = create_app()
