"""Read path and retention for the sync conflict log (M4.1 Sprint 1, #24)."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.sync_conflict import SyncConflict
from app.schemas.sync import SyncEntityType

logger = logging.getLogger(__name__)

_NOTE_FIELD = "note"
_REDACTED_NOTE_VALUE = {"present": True, "changed": True, "redacted": True}
_FORBIDDEN_NOTE_KEYS = frozenset({"text", "note", "plaintext", "content", "value"})


def sanitize_conflict_value(field_name: str, value: dict[str, Any] | None) -> dict[str, Any] | None:
    """Ensure note conflicts never leak plaintext on the wire."""
    if value is None:
        return None
    if field_name != _NOTE_FIELD:
        return value

    if any(key in value for key in _FORBIDDEN_NOTE_KEYS):
        return dict(_REDACTED_NOTE_VALUE)
    return value


async def create_sync_conflict(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    entity_id: uuid.UUID,
    entity_type: SyncEntityType,
    field_name: str,
    client_value: dict[str, Any] | None,
    server_value: dict[str, Any] | None,
    client_ts: datetime,
    server_ts: datetime,
) -> SyncConflict:
    """Persist a conflict row (used by Sprint 2 merge path and tests)."""
    row = SyncConflict(
        user_id=user_id,
        entity_id=entity_id,
        entity_type=entity_type,
        field_name=field_name,
        client_value=sanitize_conflict_value(field_name, client_value),
        server_value=sanitize_conflict_value(field_name, server_value),
        client_ts=client_ts,
        server_ts=server_ts,
    )
    db.add(row)
    await db.flush()
    return row


async def list_sync_conflicts(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    entity_type: SyncEntityType | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[SyncConflict], int]:
    """Return conflict rows newest-first plus total count for pagination."""
    filters = [SyncConflict.user_id == user_id]
    if entity_type is not None:
        filters.append(SyncConflict.entity_type == entity_type)

    total_result = await db.execute(select(func.count()).select_from(SyncConflict).where(*filters))
    total = int(total_result.scalar_one())

    rows_result = await db.execute(
        select(SyncConflict)
        .where(*filters)
        .order_by(SyncConflict.created_at.desc(), SyncConflict.id.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(rows_result.scalars().all()), total


async def cleanup_stale_sync_conflicts(
    db: AsyncSession,
    *,
    now: datetime | None = None,
    retention_days: int | None = None,
) -> int:
    """Delete conflict rows older than the retention window."""
    effective_now = now or datetime.now(UTC)
    days = retention_days if retention_days is not None else settings.SYNC_CONFLICT_RETENTION_DAYS
    threshold = effective_now - timedelta(days=days)

    result = await db.execute(
        delete(SyncConflict).where(SyncConflict.created_at < threshold).returning(SyncConflict.id)
    )
    deleted_ids = [str(row_id) for row_id in result.scalars().all()]

    logger.info(
        "sync conflict cleanup completed",
        extra={
            "deleted_count": len(deleted_ids),
            "retention_days": days,
        },
    )
    return len(deleted_ids)
