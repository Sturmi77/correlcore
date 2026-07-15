"""User consent helpers for DSGVO Art. 9 explicit consent (Issue #31)."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.consent_log import ConsentLog
from app.schemas.consent import ConsentRecordRequest, ConsentStatusItem


async def record_consent(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    payload: ConsentRecordRequest,
) -> ConsentLog:
    """Append a consent grant or revocation row."""
    entry = ConsentLog(
        user_id=user_id,
        consent_type=payload.type.strip(),
        consent_version=payload.version.strip(),
        granted=payload.granted,
    )
    db.add(entry)
    await db.flush()
    await db.refresh(entry)
    return entry


async def revoke_consent(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    consent_type: str,
    consent_version: str,
) -> ConsentLog:
    """Append a revocation row (granted=false) for the given consent type."""
    return await record_consent(
        db,
        user_id=user_id,
        payload=ConsentRecordRequest(
            type=consent_type,
            version=consent_version,
            granted=False,
        ),
    )


async def list_consent_history(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> list[ConsentLog]:
    """Return all consent events for the user, newest first."""
    result = await db.execute(
        select(ConsentLog)
        .where(ConsentLog.user_id == user_id)
        .order_by(ConsentLog.created_at.desc())
    )
    return list(result.scalars().all())


def summarize_current_consents(history: Sequence[ConsentLog]) -> list[ConsentStatusItem]:
    """Derive the latest state per consent type from audit history."""
    latest_by_type: dict[str, ConsentLog] = {}
    for entry in history:
        if entry.consent_type not in latest_by_type:
            latest_by_type[entry.consent_type] = entry

    items = [
        ConsentStatusItem(
            consent_type=entry.consent_type,
            consent_version=entry.consent_version,
            granted=entry.granted,
            updated_at=entry.created_at,
        )
        for entry in latest_by_type.values()
    ]
    items.sort(key=lambda item: item.consent_type)
    return items


async def is_consent_granted(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    consent_type: str,
) -> bool:
    """Return whether the latest event for ``consent_type`` is a grant."""
    result = await db.execute(
        select(ConsentLog)
        .where(
            ConsentLog.user_id == user_id,
            ConsentLog.consent_type == consent_type,
        )
        .order_by(ConsentLog.created_at.desc())
        .limit(1)
    )
    latest = result.scalar_one_or_none()
    return latest is not None and latest.granted
