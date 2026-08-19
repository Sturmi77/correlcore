"""API v1 router — aggregates all sub-routers."""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    admin,
    analysis,
    auth,
    dashboard,
    dev,
    devices,
    entries,
    export,
    habits,
    health,
    health_connect,
    insights,
    instance,
    media,
    note_markers,
    note_signals,
    onboarding,
    symptoms,
    sync,
    tags,
    user,
    widget,
)

api_router = APIRouter()

# Internal health probes
api_router.include_router(health.router, prefix="/health", tags=["internal"])

# Public deployment descriptor (hosted vs selfhost, registration, version)
api_router.include_router(instance.router, prefix="/instance", tags=["internal"])

# Feature-flagged developer diagnostics (Issue #125)
api_router.include_router(dev.router, prefix="/dev", tags=["internal"])

# Auth
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])

# User self-management (M1, Issue #66) — currently only DELETE /user/me
# (DSGVO Art. 17 erasure). Future M2+: GET /user/me, PATCH /user/me,
# data-export endpoints (Issue #25).
api_router.include_router(user.router, prefix="/user", tags=["user"])

api_router.include_router(admin.router, prefix="/admin", tags=["admin"])

# Device push tokens (M11 Sprint 5 — FCM; UnifiedPush provider reserved for M4.2)
api_router.include_router(devices.router, prefix="/devices", tags=["devices"])

# M2 convenience data exports (canonical DSGVO ZIP lives under /user/export)
api_router.include_router(export.router, prefix="/export", tags=["export"])

# Daily entries (M1, Issue #7)
api_router.include_router(entries.router, prefix="/entries", tags=["entries"])
api_router.include_router(
    note_markers.entry_note_markers_router,
    prefix="/entries",
    tags=["entries"],
)
api_router.include_router(
    note_signals.entry_note_signals_router,
    prefix="/entries",
    tags=["entries"],
)
api_router.include_router(
    note_signals.admin_note_signals_router,
    prefix="/admin",
    tags=["admin"],
)

# Notes in analysis (M3 retroactive)
api_router.include_router(analysis.router, prefix="/analysis", tags=["analysis"])

# Dashboard summary (M3 insight confidence scale)
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])

# Android Glance widget summary (M11 Sprint 4)
api_router.include_router(widget.router, prefix="/widget", tags=["widget"])

# M3 generated insights (read-only API surface; worker generation is scheduled)
api_router.include_router(insights.router, prefix="/insights", tags=["insights"])

# M8 Sprint 4 — Health Connect sleep import (consent-gated)
api_router.include_router(health_connect.router, prefix="/health-connect", tags=["health-connect"])

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

# M13 foundation — photo upload with mandatory EXIF strip (Issue #28).
api_router.include_router(media.router, prefix="/media", tags=["media"])

api_router.include_router(sync.router, prefix="/sync", tags=["sync"])

# Future routers (M1+):
