"""Health check endpoints — three distinct probes (DESIGN_DOCUMENT.md §3.6).

GET /health/live   — liveness:  is the process alive?          (Docker HC)
GET /health/ready  — readiness: are external deps reachable?   (Traefik / Uptime-Kuma)
GET /health        — summary:   human-readable aggregated view

Semantics
---------
- /live  must *never* return 5xx due to DB/Redis issues — that would cause
  unnecessary container restarts.
- /ready returns 503 when any required dependency is down.
- /health (summary) always returns 200 with the aggregated state embedded
  in the JSON body so a browser / ops person can read it at a glance.
"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.services.health_service import (
    ComponentHealth,
    check_liveness,
    check_readiness,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

class LivenessResponse(BaseModel):
    status: str
    version: str


class ComponentModel(BaseModel):
    name: str
    status: str
    detail: str = ""


class ReadinessResponse(BaseModel):
    status: str
    components: list[ComponentModel]


class HealthSummary(BaseModel):
    status: str
    version: str
    readiness: ReadinessResponse


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get(
    "/live",
    response_model=LivenessResponse,
    summary="Liveness probe",
    description=(
        "Returns 200 as long as the API process is running. "
        "Does **not** check external dependencies — safe to use as Docker "
        "HEALTHCHECK without risk of restart loops during transient DB outages."
    ),
    tags=["internal"],
)
async def liveness() -> LivenessResponse:
    data = check_liveness()
    return LivenessResponse(**data)


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    summary="Readiness probe",
    description=(
        "Returns 200 when all required dependencies (PostgreSQL, Redis) are "
        "reachable. Returns 503 otherwise. Use this for load-balancer / "
        "reverse-proxy health checks."
    ),
    tags=["internal"],
)
async def readiness() -> JSONResponse:
    report = await check_readiness()
    body = ReadinessResponse(
        status=report.status,
        components=[
            ComponentModel(name=c.name, status=c.status.value, detail=c.detail)
            for c in report.components
        ],
    )
    status_code = 200 if report.ready else 503
    return JSONResponse(content=body.model_dump(), status_code=status_code)


@router.get(
    "",
    response_model=HealthSummary,
    summary="Health summary",
    description="Human-readable aggregated health view. Always returns HTTP 200.",
    tags=["internal"],
)
async def health_summary() -> HealthSummary:
    liveness_data = check_liveness()
    report = await check_readiness()
    readiness_body = ReadinessResponse(
        status=report.status,
        components=[
            ComponentModel(name=c.name, status=c.status.value, detail=c.detail)
            for c in report.components
        ],
    )
    overall = "ok" if report.ready else "degraded"
    return HealthSummary(
        status=overall,
        version=liveness_data["version"],
        readiness=readiness_body,
    )
