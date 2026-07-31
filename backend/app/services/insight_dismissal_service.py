"""Subject-stable insight dismissals (#601 Phase 1)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.insight import Insight
from app.models.insight_dismissal import InsightDismissal
from app.services.insight_service import (
    MAX_INSIGHT_LIST_LIMIT,
    InsightNotFoundError,
    _tag_slugs_for_legacy_insights,
    get_insight_by_id,
    insight_subject_key,
)
from app.services.user_preferences_service import (
    get_dismissed_insight_keys,
    remove_dismissed_insight_keys,
)


class InsightDismissalNotFoundError(Exception):
    def __init__(self, dismissal_id: uuid.UUID) -> None:
        super().__init__(f"Insight dismissal not found: {dismissal_id}")
        self.dismissal_id = dismissal_id


@dataclass(frozen=True)
class InsightDismissalView:
    dismissal: InsightDismissal
    insight: Insight | None


def _parse_uuid(value: str) -> uuid.UUID | None:
    try:
        return uuid.UUID(value)
    except ValueError:
        return None


async def list_dismissed_subject_keys(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> set[str]:
    result = await db.execute(
        select(InsightDismissal.subject_key).where(InsightDismissal.user_id == user_id)
    )
    return {row[0] for row in result.all()}


async def migrate_uuid_prefs_to_subject_dismissals(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> int:
    """Convert UUID entries in ``dismissed_insight_keys`` into dismissal rows.

    Banner keys (non-UUID) stay in preferences. Returns number of migrated keys.
    """

    keys = await get_dismissed_insight_keys(db, user_id=user_id)
    uuid_keys: list[uuid.UUID] = []
    for key in keys:
        parsed = _parse_uuid(key)
        if parsed is not None:
            uuid_keys.append(parsed)
    if not uuid_keys:
        return 0

    result = await db.execute(
        select(Insight).where(Insight.user_id == user_id, Insight.id.in_(uuid_keys))
    )
    insights = list(result.scalars().all())
    if not insights:
        return 0

    tag_slugs_by_id = await _tag_slugs_for_legacy_insights(db, insights)
    existing = await list_dismissed_subject_keys(db, user_id=user_id)
    migrated: list[str] = []
    now = datetime.now(UTC)

    for insight in insights:
        subject_key = insight_subject_key(insight, tag_slugs_by_id=tag_slugs_by_id)
        if subject_key not in existing:
            db.add(
                InsightDismissal(
                    user_id=user_id,
                    subject_key=subject_key,
                    insight_id=insight.id,
                    dismissed_at=now,
                )
            )
            existing.add(subject_key)
        migrated.append(str(insight.id))

    if migrated:
        await remove_dismissed_insight_keys(db, user_id=user_id, keys=migrated)
        await db.flush()
    return len(migrated)


async def create_insight_dismissal(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    insight_id: uuid.UUID,
) -> InsightDismissal:
    """Hide an insight by subject key (idempotent upsert)."""

    insight = await get_insight_by_id(db, user_id=user_id, insight_id=insight_id)
    tag_slugs_by_id = await _tag_slugs_for_legacy_insights(db, [insight])
    subject_key = insight_subject_key(insight, tag_slugs_by_id=tag_slugs_by_id)

    result = await db.execute(
        select(InsightDismissal).where(
            InsightDismissal.user_id == user_id,
            InsightDismissal.subject_key == subject_key,
        )
    )
    row = result.scalar_one_or_none()
    now = datetime.now(UTC)
    if row is None:
        row = InsightDismissal(
            user_id=user_id,
            subject_key=subject_key,
            insight_id=insight.id,
            dismissed_at=now,
        )
        db.add(row)
    else:
        row.insight_id = insight.id
        row.dismissed_at = now

    # Drop legacy UUID pref key for this insight if present.
    await remove_dismissed_insight_keys(db, user_id=user_id, keys=[str(insight.id)])
    await db.flush()
    await db.refresh(row)
    return row


async def delete_insight_dismissal(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    dismissal_id: uuid.UUID,
) -> None:
    result = await db.execute(
        select(InsightDismissal).where(
            InsightDismissal.id == dismissal_id,
            InsightDismissal.user_id == user_id,
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise InsightDismissalNotFoundError(dismissal_id)
    await db.delete(row)
    await db.flush()


async def delete_insight_dismissal_by_insight_id(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    insight_id: uuid.UUID,
) -> None:
    """Undo hide for the subject of ``insight_id`` (or legacy UUID pref)."""

    result = await db.execute(
        select(InsightDismissal).where(
            InsightDismissal.user_id == user_id,
            InsightDismissal.insight_id == insight_id,
        )
    )
    row = result.scalar_one_or_none()
    if row is not None:
        await db.delete(row)
        await db.flush()
        await remove_dismissed_insight_keys(db, user_id=user_id, keys=[str(insight_id)])
        return

    try:
        insight = await get_insight_by_id(db, user_id=user_id, insight_id=insight_id)
    except InsightNotFoundError:
        await remove_dismissed_insight_keys(db, user_id=user_id, keys=[str(insight_id)])
        return

    tag_slugs_by_id = await _tag_slugs_for_legacy_insights(db, [insight])
    subject_key = insight_subject_key(insight, tag_slugs_by_id=tag_slugs_by_id)
    result = await db.execute(
        select(InsightDismissal).where(
            InsightDismissal.user_id == user_id,
            InsightDismissal.subject_key == subject_key,
        )
    )
    row = result.scalar_one_or_none()
    if row is not None:
        await db.delete(row)
        await db.flush()
    await remove_dismissed_insight_keys(db, user_id=user_id, keys=[str(insight_id)])


async def list_insight_dismissals(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> list[InsightDismissalView]:
    """Return dismissals newest-first, hydrated with a matching live insight when possible."""

    await migrate_uuid_prefs_to_subject_dismissals(db, user_id=user_id)

    result = await db.execute(
        select(InsightDismissal)
        .where(InsightDismissal.user_id == user_id)
        .order_by(InsightDismissal.dismissed_at.desc(), InsightDismissal.created_at.desc())
    )
    dismissals = list(result.scalars().all())
    if not dismissals:
        return []

    insights_result = await db.execute(
        select(Insight)
        .where(Insight.user_id == user_id)
        .order_by(Insight.generated_at.desc(), Insight.created_at.desc())
        .limit(MAX_INSIGHT_LIST_LIMIT)
    )
    insights = list(insights_result.scalars().all())
    tag_slugs_by_id = await _tag_slugs_for_legacy_insights(db, insights)

    newest_by_subject: dict[str, Insight] = {}
    for insight in insights:
        key = insight_subject_key(insight, tag_slugs_by_id=tag_slugs_by_id)
        if key not in newest_by_subject:
            newest_by_subject[key] = insight

    by_id = {insight.id: insight for insight in insights}
    views: list[InsightDismissalView] = []
    for dismissal in dismissals:
        insight = newest_by_subject.get(dismissal.subject_key)
        if insight is None and dismissal.insight_id is not None:
            insight = by_id.get(dismissal.insight_id)
        if insight is not None and dismissal.insight_id != insight.id:
            dismissal.insight_id = insight.id
        views.append(InsightDismissalView(dismissal=dismissal, insight=insight))

    await db.flush()
    return views


async def dismissed_uuid_keys_remaining(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> set[str]:
    """UUID keys still in prefs (unmigrated / orphan); banner keys excluded."""

    keys = await get_dismissed_insight_keys(db, user_id=user_id)
    return {key for key in keys if _parse_uuid(key) is not None}
