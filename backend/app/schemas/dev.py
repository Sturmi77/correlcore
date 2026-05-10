"""Developer diagnostics schemas.

The developer view is feature-flagged and authenticated because it exposes
deployment and infrastructure metadata.
"""

from __future__ import annotations

from pydantic import BaseModel


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
