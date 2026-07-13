"""Feature-flagged developer diagnostics endpoint."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps.auth import get_current_verified_user
from app.core.config import settings
from app.db.session import get_session
from app.models.user import User
from app.models.worker_run import WorkerRun
from app.schemas.dev import (
    DevDbBackupCreateResponse,
    DevDbBackupItem,
    DevDbBackupListResponse,
    DevDbRestoreRequest,
    DevDbRestoreResponse,
    DevInfoResponse,
    DevInsightsRunResponse,
    WorkerRunResponse,
    WorkerRunsLatestResponse,
    WorkerRunsListResponse,
)
from app.services import worker_run_service
from app.services.dev_db_service import DevDbOpsError, create_backup, list_backups, restore_backup
from app.services.dev_service import _db_migration_head, build_dev_info
from app.workers.analytics import run_insights_once

router = APIRouter()


def require_dev_view_enabled() -> None:
    if not settings.DEV_VIEW_ENABLED:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")


def require_dev_db_ops() -> None:
    require_dev_view_enabled()
    if settings.APP_ENV.lower() not in {"development", "test"}:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")


def _to_run_response(run: WorkerRun | None) -> WorkerRunResponse | None:
    if run is None:
        return None
    return WorkerRunResponse(
        id=run.id,
        worker_name=run.worker_name,
        job_kind=run.job_kind.value,
        trigger_source=run.trigger_source.value,
        status=run.status.value,
        started_at=run.started_at,
        finished_at=run.finished_at,
        scope_user_id=run.scope_user_id,
        result=run.result or {},
        error_message=run.error_message,
    )


@router.get(
    "/info",
    response_model=DevInfoResponse,
    summary="Developer runtime and infrastructure diagnostics",
)
async def dev_info(
    _flag: None = Depends(require_dev_view_enabled),
    _user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_session),
) -> DevInfoResponse:
    return await build_dev_info(db)


@router.get(
    "/workers",
    response_model=WorkerRunsListResponse,
    summary="Recent analytics worker runs",
)
async def list_dev_workers(
    _flag: None = Depends(require_dev_view_enabled),
    user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_session),
    limit: int = Query(default=20, ge=1, le=100),
    scope: Literal["all", "me"] = Query(default="all"),
) -> WorkerRunsListResponse:
    runs = await worker_run_service.list_worker_runs(
        db,
        limit=limit,
        scope_user_id=user.id,
        scope=scope,
    )
    return WorkerRunsListResponse(
        items=[item for item in (_to_run_response(run) for run in runs) if item is not None],
        ops_ready=False,
    )


@router.get(
    "/workers/latest",
    response_model=WorkerRunsLatestResponse,
    summary="Latest worker run cards for GUI validation",
)
async def latest_dev_workers(
    _flag: None = Depends(require_dev_view_enabled),
    user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_session),
) -> WorkerRunsLatestResponse:
    latest = await worker_run_service.latest_worker_runs(db, scope_user_id=user.id)
    return WorkerRunsLatestResponse(
        daily_bundle=_to_run_response(latest["daily_bundle"]),
        fleet_insights=_to_run_response(latest["fleet_insights"]),
        user_insights=_to_run_response(latest["user_insights"]),
        ops_ready=False,
    )


@router.post(
    "/workers/insights/run-once",
    response_model=DevInsightsRunResponse,
    summary="Run fleet insight generation once (development)",
)
async def run_insights_dev_once(
    _flag: None = Depends(require_dev_db_ops),
    _user: User = Depends(get_current_verified_user),
) -> DevInsightsRunResponse:
    summary = await run_insights_once(trigger_source="dev_trigger")
    return DevInsightsRunResponse(
        eligible_users=summary.eligible_users,
        processed_users=summary.processed_users,
        failed_users=summary.failed_users,
        generated_insights=summary.generated_insights,
    )


@router.get(
    "/db/backups",
    response_model=DevDbBackupListResponse,
    summary="List local development database dumps",
)
async def list_dev_db_backups(
    _flag: None = Depends(require_dev_db_ops),
    _user: User = Depends(get_current_verified_user),
) -> DevDbBackupListResponse:
    try:
        items, backup_dir = list_backups()
    except DevDbOpsError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return DevDbBackupListResponse(
        items=[DevDbBackupItem(**item) for item in items],
        backup_dir=backup_dir,
        ops_ready=False,
        encryption_key_required=True,
    )


@router.post(
    "/db/backups",
    response_model=DevDbBackupCreateResponse,
    summary="Create a local development database dump",
)
async def create_dev_db_backup(
    _flag: None = Depends(require_dev_db_ops),
    _user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_session),
) -> DevDbBackupCreateResponse:
    try:
        head = await _db_migration_head(db)
        backup = create_backup(alembic_head=head)
    except DevDbOpsError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return DevDbBackupCreateResponse(
        backup=DevDbBackupItem(**backup),
        message=(
            "Dump created. Store ENCRYPTION_KEY alongside the dump; "
            "ops_ready remains false (development-only)."
        ),
    )


@router.post(
    "/db/restore",
    response_model=DevDbRestoreResponse,
    summary="Restore a local development database dump",
)
async def restore_dev_db_backup(
    body: DevDbRestoreRequest,
    _flag: None = Depends(require_dev_db_ops),
    _user: User = Depends(get_current_verified_user),
) -> DevDbRestoreResponse:
    try:
        result = restore_backup(body.name, confirm=body.confirm)
    except DevDbOpsError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return DevDbRestoreResponse(
        restored=result["restored"],
        message=result["message"],
        ops_ready=False,
    )
