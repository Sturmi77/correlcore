"""Developer diagnostics schemas.

The developer view is feature-flagged and authenticated because it exposes
deployment and infrastructure metadata. Worker/DB tooling stays under the same
gate; backup/restore additionally requires APP_ENV=development.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class DevInfoResponse(BaseModel):
    image_hash: str
    image_digest: str | None
    image_tag: str
    build_time: str | None
    git_commit: str
    git_branch: str
    python_version: str
    fastapi_version: str
    db_migration_head: str | None
    db_pool_size: int | None
    db_checked_out: int | None
    redis_connected: bool
    minio_connected: bool
    health_ready: bool
    uptime_seconds: int


class WorkerRunResponse(BaseModel):
    id: UUID
    worker_name: str
    job_kind: str
    trigger_source: str
    status: str
    started_at: datetime
    finished_at: datetime | None
    scope_user_id: UUID | None
    result: dict[str, Any]
    error_message: str | None


class WorkerRunsListResponse(BaseModel):
    items: list[WorkerRunResponse]
    ops_ready: bool = Field(
        default=False,
        description="Reserved for future production ops tooling; always false in v1.",
    )


class WorkerRunsLatestResponse(BaseModel):
    daily_bundle: WorkerRunResponse | None
    fleet_insights: WorkerRunResponse | None
    user_insights: WorkerRunResponse | None
    ops_ready: bool = False


class DevInsightsRunResponse(BaseModel):
    status: Literal["ok"] = "ok"
    eligible_users: int
    processed_users: int
    failed_users: int
    generated_insights: int


class DevDbBackupItem(BaseModel):
    name: str
    size_bytes: int
    created_at: datetime
    meta: dict[str, Any] | None = None


class DevDbBackupListResponse(BaseModel):
    items: list[DevDbBackupItem]
    backup_dir: str
    ops_ready: bool = False
    encryption_key_required: bool = True


class DevDbBackupCreateResponse(BaseModel):
    status: Literal["ok"] = "ok"
    backup: DevDbBackupItem
    message: str


class DevDbRestoreRequest(BaseModel):
    name: str
    confirm: bool = False


class DevDbRestoreResponse(BaseModel):
    status: Literal["ok"] = "ok"
    restored: str
    message: str
    ops_ready: bool = False
