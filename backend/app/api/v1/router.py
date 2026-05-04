"""API v1 router — aggregates all sub-routers."""

from fastapi import APIRouter

from app.api.v1.endpoints import auth, entries, health

api_router = APIRouter()

# Internal health probes
api_router.include_router(health.router, prefix="/health", tags=["internal"])

# Auth
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])

# Daily entries (M1, Issue #7)
api_router.include_router(entries.router, prefix="/entries", tags=["entries"])

# Future routers (M1+):
# api_router.include_router(tags_router.router, prefix="/tags", tags=["tags"])
# api_router.include_router(sync.router, prefix="/sync", tags=["sync"])
# api_router.include_router(insights.router, prefix="/insights", tags=["insights"])
