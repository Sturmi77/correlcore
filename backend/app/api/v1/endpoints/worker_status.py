"""Worker freshness/monitoring endpoint (#756).

``GET /worker/status`` exposes the age and status of the last *successful*
run per monitored :class:`~app.models.worker_run.WorkerJobKind`, so an
external uptime tool (Uptime-Kuma, healthchecks.io) or a GlitchTip cron
monitor can alert when the nightly worker silently stops making progress —
as opposed to crashing loudly, which #745 Phase 4 already covers via
GlitchTip error tracking.

This complements, rather than replaces, container-level liveness: a
long-running process can stay "alive" (PID present, port open) while no
longer completing its nightly work — this endpoint is the actual "did the
work happen" signal that #757 wires into monitoring once the worker moves
from a durable process to externally-triggered ``--once`` runs.

Auth (never fully unauthenticated — see #756's requirement to not expose
this unprotected on hosted deployments): either

- header ``X-Worker-Status-Key: <WORKER_STATUS_API_KEY>`` — for external
  monitors that cannot hold a browser session, or
- an existing verified + admin user session — for manual/admin inspection.

If ``WORKER_STATUS_API_KEY`` is unset, only the admin-session path applies.
"""

from __future__ import annotations

import hmac
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps.auth import get_current_user_lax
from app.core.config import settings
from app.db.session import get_session
from app.models.user import User
from app.models.worker_run import WorkerJobKind, WorkerRun
from app.services.worker_run_service import MONITORED_KINDS, latest_successful_system_runs

router = APIRouter()

# Weekly-cadence job kinds get a proportionally larger staleness window than
# WORKER_STALE_AFTER_HOURS (which assumes the ~24h nightly cadence) — a job
# that by design only runs once a week (weekly digest, piggybacked on the
# Sunday daily-bundle slot, see app.workers.analytics.DIGEST_WEEKDAY) must
# not be flagged "stale" every Monday through Saturday.
_WEEKLY_CADENCE_MULTIPLIER: dict[WorkerJobKind, int] = {
    WorkerJobKind.DIGEST: 7,
}


def _stale_after_hours(job_kind: WorkerJobKind) -> int:
    multiplier = _WEEKLY_CADENCE_MULTIPLIER.get(job_kind, 1)
    return settings.WORKER_STALE_AFTER_HOURS * multiplier


class WorkerJobFreshness(BaseModel):
    """Freshness snapshot for a single monitored job kind.

    ``job_status`` distinguishes "never ran yet" (e.g. a freshly deployed
    instance that hasn't reached its first 03:00 UTC slot) from "ran before
    but has since gone stale" — both set ``stale=True`` (per #756's literal
    wording: alert when no successful run exists within the threshold, which
    a run that never happened vacuously satisfies), but operators reading
    the response manually benefit from telling a brand-new install apart
    from a worker that used to work and stopped.
    """

    job_kind: str
    job_status: str  # "fresh" | "stale" | "never_run"
    last_success_at: datetime | None
    age_hours: float | None
    stale_after_hours: int
    stale: bool


class WorkerStatusResponse(BaseModel):
    """Aggregate freshness report used by external monitoring."""

    status: str  # "ok" | "stale"
    generated_at: datetime
    jobs: list[WorkerJobFreshness]


async def require_worker_status_access(
    x_worker_status_key: str | None = Header(default=None, alias="X-Worker-Status-Key"),
    current_user: User | None = Depends(get_current_user_lax),
) -> None:
    """Allow either the configured monitoring API key or an admin session.

    Mirrors the two options named in #756 ("API-Key oder Admin-Auth"):
    external uptime monitors cannot hold a browser session, so they
    authenticate with a static key instead; humans inspecting the endpoint
    manually reuse their existing admin login (``is_admin`` DB flag, same
    check as :func:`app.api.v1.deps.auth.require_admin`).
    """

    configured_key = settings.WORKER_STATUS_API_KEY
    if configured_key and x_worker_status_key is not None:
        if hmac.compare_digest(x_worker_status_key, configured_key):
            return
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid worker status key",
        )

    if current_user is not None and current_user.is_verified and current_user.is_admin:
        return

    # Opaque 401 regardless of *why* auth failed (missing key vs. missing/
    # non-admin session) — mirrors the existing credentials-exception
    # convention in app.api.v1.deps.auth, so this endpoint doesn't leak
    # whether a key was configured at all to an unauthenticated caller.
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
    )


def _build_job_freshness(
    job_kind: WorkerJobKind,
    run: WorkerRun | None,
    *,
    now: datetime,
) -> WorkerJobFreshness:
    threshold = _stale_after_hours(job_kind)
    if run is None or run.finished_at is None:
        return WorkerJobFreshness(
            job_kind=job_kind.value,
            job_status="never_run",
            last_success_at=None,
            age_hours=None,
            stale_after_hours=threshold,
            stale=True,
        )
    finished_at = run.finished_at if run.finished_at.tzinfo else run.finished_at.replace(tzinfo=UTC)
    age_hours = (now - finished_at).total_seconds() / 3600
    is_stale = age_hours > threshold
    return WorkerJobFreshness(
        job_kind=job_kind.value,
        job_status="stale" if is_stale else "fresh",
        last_success_at=finished_at,
        age_hours=round(age_hours, 2),
        stale_after_hours=threshold,
        stale=is_stale,
    )


@router.get(
    "/status",
    response_model=WorkerStatusResponse,
    dependencies=[Depends(require_worker_status_access)],
)
async def get_worker_status(
    db: AsyncSession = Depends(get_session),
) -> WorkerStatusResponse:
    """Report freshness of the last successful run per monitored job kind."""

    now = datetime.now(UTC)
    runs = await latest_successful_system_runs(db, kinds=MONITORED_KINDS)
    jobs = [_build_job_freshness(kind, runs.get(kind), now=now) for kind in MONITORED_KINDS]
    overall_status = "stale" if any(job.stale for job in jobs) else "ok"
    return WorkerStatusResponse(status=overall_status, generated_at=now, jobs=jobs)
