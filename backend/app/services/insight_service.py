"""Read-only service helpers for M3 insights."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entry import Entry
from app.models.insight import Insight
from app.models.tag import Tag
from app.schemas.insight import InsightMaturity, InsightMaturityPhase

DEFAULT_INSIGHT_LIST_LIMIT = 50
MAX_INSIGHT_LIST_LIMIT = 200
DEFAULT_LATEST_INSIGHT_LIMIT = 10
MAX_LATEST_INSIGHT_LIMIT = 50


def _clamp_limit(limit: int, *, default: int, maximum: int) -> int:
    if limit <= 0:
        return default
    return min(limit, maximum)


def calculate_insight_maturity(entry_count: int) -> InsightMaturity:
    """Map tracked entry count to the ADR-0021 insight maturity phase."""

    count = max(entry_count, 0)
    if count >= 30:
        return InsightMaturity(
            phase=InsightMaturityPhase.ROBUST,
            phase_index=4,
            current_entries=count,
            next_phase_at=None,
            next_phase_label=None,
            entries_until_next=None,
            user_message_key="maturity.robust.description",
        )
    if count >= 14:
        return InsightMaturity(
            phase=InsightMaturityPhase.PROVISIONAL,
            phase_index=3,
            current_entries=count,
            next_phase_at=30,
            next_phase_label="Robust Insights",
            entries_until_next=30 - count,
            user_message_key="maturity.provisional.description",
        )
    if count >= 7:
        return InsightMaturity(
            phase=InsightMaturityPhase.EARLY_PATTERNS,
            phase_index=2,
            current_entries=count,
            next_phase_at=14,
            next_phase_label="Provisional Insights",
            entries_until_next=14 - count,
            user_message_key="maturity.early_patterns.description",
        )
    return InsightMaturity(
        phase=InsightMaturityPhase.COLLECTING,
        phase_index=1,
        current_entries=count,
        next_phase_at=7,
        next_phase_label="First Patterns",
        entries_until_next=7 - count,
        user_message_key="maturity.collecting.description",
    )


async def get_insight_maturity(db: AsyncSession, *, user_id: uuid.UUID) -> InsightMaturity:
    """Return the current insight maturity based on tracked entry days."""

    result = await db.execute(
        select(func.count(func.distinct(Entry.entry_date))).where(Entry.user_id == user_id)
    )
    entry_count = int(result.scalar_one() or 0)
    return calculate_insight_maturity(entry_count)


async def list_insights(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    limit: int = DEFAULT_INSIGHT_LIST_LIMIT,
) -> list[Insight]:
    """Return newest insight rows for a user."""

    limit = _clamp_limit(limit, default=DEFAULT_INSIGHT_LIST_LIMIT, maximum=MAX_INSIGHT_LIST_LIMIT)
    result = await db.execute(
        select(Insight)
        .where(Insight.user_id == user_id)
        .order_by(Insight.generated_at.desc(), Insight.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


def _latest_metric_key(insight: Insight) -> str:
    if insight.insight_type == "pointbiserial" and insight.subject_type == "tag":
        if insight.metric in {"mood", "mood_score", "mood_avg"}:
            return "mood_score"
    return insight.metric


def _normalise_label(value: str) -> str:
    return " ".join(value.casefold().split())


def _latest_subject_key(
    insight: Insight,
    *,
    tag_slugs_by_id: dict[uuid.UUID, str],
) -> tuple[object, ...]:
    """Return the semantic subject key used by /insights/latest.

    Tag insights may be generated from historical default-tag IDs and newer
    copy-on-write override IDs. When the analytics payload includes a slug, use
    it as the canonical key; otherwise fall back to a case-insensitive label so
    older generated rows still collapse in the UI.
    """

    if insight.subject_type == "tag":
        tag_slug = insight.payload.get("tag_slug") if isinstance(insight.payload, dict) else None
        if isinstance(tag_slug, str) and tag_slug:
            return ("tag_slug", tag_slug.casefold())
        if insight.subject_id and insight.subject_id in tag_slugs_by_id:
            return ("tag_slug", tag_slugs_by_id[insight.subject_id].casefold())
        if insight.subject_label:
            return ("tag_label", _normalise_label(insight.subject_label))
    return ("subject", insight.subject_id, insight.subject_label)


async def _tag_slugs_for_legacy_insights(
    db: AsyncSession,
    insights: list[Insight],
) -> dict[uuid.UUID, str]:
    tag_ids = {
        insight.subject_id
        for insight in insights
        if insight.subject_type == "tag"
        and insight.subject_id is not None
        and not (
            isinstance(insight.payload, dict)
            and isinstance(insight.payload.get("tag_slug"), str)
            and insight.payload.get("tag_slug")
        )
    }
    if not tag_ids:
        return {}
    result = await db.execute(select(Tag.id, Tag.slug).where(Tag.id.in_(tag_ids)))
    return {tag_id: slug for tag_id, slug in result.all()}


async def list_latest_insights(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    limit: int = DEFAULT_LATEST_INSIGHT_LIMIT,
) -> list[Insight]:
    """Return the newest insight per analytical subject.

    A subject is the tuple of insight family, metric and optional target
    (metric/tag/weekday). Keeping this de-duplication in Python avoids
    Postgres-specific ``DISTINCT ON`` so service tests stay simple while the
    DB query remains owner-filtered and newest-first.
    """

    limit = _clamp_limit(
        limit,
        default=DEFAULT_LATEST_INSIGHT_LIMIT,
        maximum=MAX_LATEST_INSIGHT_LIMIT,
    )
    result = await db.execute(
        select(Insight)
        .where(Insight.user_id == user_id)
        .order_by(Insight.generated_at.desc(), Insight.created_at.desc())
        .limit(MAX_INSIGHT_LIST_LIMIT)
    )

    insights = list(result.scalars().all())
    tag_slugs_by_id = await _tag_slugs_for_legacy_insights(db, insights)

    latest: list[Insight] = []
    seen: set[tuple[object, ...]] = set()
    for insight in insights:
        key = (
            insight.insight_type,
            _latest_metric_key(insight),
            insight.subject_type,
            _latest_subject_key(insight, tag_slugs_by_id=tag_slugs_by_id),
        )
        if key in seen:
            continue
        seen.add(key)
        latest.append(insight)
        if len(latest) >= limit:
            break
    return latest
