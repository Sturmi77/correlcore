"""API v1 router — aggregates all sub-routers."""

from fastapi import APIRouter

from app.api.v1.endpoints import auth, entries, health, symptoms, tags

api_router = APIRouter()

# Internal health probes
api_router.include_router(health.router, prefix="/health", tags=["internal"])

# Auth
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])

# Daily entries (M1, Issue #7)
api_router.include_router(entries.router, prefix="/entries", tags=["entries"])

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
# api_router.include_router(insights.router, prefix="/insights", tags=["insights"])
