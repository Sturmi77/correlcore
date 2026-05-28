"""API v1 router — aggregates all sub-routers."""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    dashboard,
    dev,
    entries,
    export,
    habits,
    health,
    insights,
    onboarding,
    symptoms,
    tags,
    user,
)

api_router = APIRouter()

# Internal health probes
api_router.include_router(health.router, prefix="/health", tags=["internal"])

# Feature-flagged developer diagnostics (Issue #125)
api_router.include_router(dev.router, prefix="/dev", tags=["internal"])

# Auth
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])

# User self-management (M1, Issue #66) — currently only DELETE /user/me
# (DSGVO Art. 17 erasure). Future M2+: GET /user/me, PATCH /user/me,
# data-export endpoints (Issue #25).
api_router.include_router(user.router, prefix="/user", tags=["user"])

# M2 convenience data exports (canonical DSGVO ZIP lives under /user/export)
api_router.include_router(export.router, prefix="/export", tags=["export"])

# Daily entries (M1, Issue #7)
api_router.include_router(entries.router, prefix="/entries", tags=["entries"])

# Dashboard summary (M3 insight confidence scale)
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])

# M3 generated insights (read-only API surface; worker generation is scheduled)
api_router.include_router(insights.router, prefix="/insights", tags=["insights"])

# M5 habit statistics.
api_router.include_router(habits.router, prefix="/habits", tags=["habits"])

# M4 guided onboarding.
api_router.include_router(onboarding.router, prefix="/onboarding", tags=["onboarding"])

# Tag system (M1, Issue #8) — tag CRUD under /tags, entry-tag assignment
# under /entries/{entry_id}/tags. Two routers, mounted with the right
# prefixes so the URL hierarchy stays REST-idiomatic.
api_router.include_router(tags.tags_router, prefix="/tags", tags=["tags"])
api_router.include_router(tags.entry_tags_router, prefix="/entries", tags=["tags"])

# Symptom checklist (M1, Issue #9) — standard catalogue under /symptoms,
# entry-symptom assignment under /entries/{entry_id}/symptoms. Same
# two-router pattern as tags so the URL hierarchy stays REST-idiomatic.
api_router.include_router(symptoms.symptoms_router, prefix="/symptoms", tags=["symptoms"])
api_router.include_router(symptoms.entry_symptoms_router, prefix="/entries", tags=["symptoms"])

# Future routers (M1+):
# api_router.include_router(sync.router, prefix="/sync", tags=["sync"])
