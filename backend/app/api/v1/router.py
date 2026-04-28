"""API v1 router — aggregates all sub-routers."""

from fastapi import APIRouter

from app.api.v1.endpoints import health

api_router = APIRouter()

# Health (internal) — also exposed at /health on root for Docker healthcheck
api_router.include_router(health.router, prefix="/health", tags=["internal"])

# Future routers (M0+):
# api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
# api_router.include_router(entries.router, prefix="/entries", tags=["entries"])
# api_router.include_router(tags.router, prefix="/tags", tags=["tags"])
# api_router.include_router(sync.router, prefix="/sync", tags=["sync"])
# api_router.include_router(insights.router, prefix="/insights", tags=["insights"])
