"""Read-only service helpers for M3 insights."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entry import Entry
from app.models.insight import Insight, InsightType
from app.models.tag import Tag
from app.schemas.insight import (
    InsightEventWindow,
    InsightEventWindowsResponse,
    InsightMaturity,
    InsightMaturityPhase,
)
from app.schemas.stats import TagCooccurrenceRange
from app.services.stats_service import (
    _analytics_enabled,
    _cooccurrence_window,
    cooccurrence_range_to_timeseries,
    get_timeseries,
    list_historical_tag_presence_dates_by_slug,
    list_symptom_presence_dates,
)

DEFAULT_INSIGHT_LIST_LIMIT = 50
MAX_INSIGHT_LIST_LIMIT = 200
DEFAULT_LATEST_INSIGHT_LIMIT = 10
MAX_LATEST_INSIGHT_LIMIT = 50


class InsightNotFoundError(Exception):
    def __init__(self, insight_id: uuid.UUID) -> None:
        self.insight_id = insight_id
        super().__init__(f"Insight {insight_id} not found")


class InsightEventWindowsUnsupportedError(Exception):
    """Raised when an insight subject cannot produce event-aligned windows."""

    def __init__(self, subject_type: str | None) -> None:
        self.subject_type = subject_type
        super().__init__(f"Event windows unsupported for subject_type={subject_type!r}")


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


def _payload_key(value: object) -> object:
    if isinstance(value, dict):
        parts = []
        for key in ("kind", "key", "id", "slug", "name"):
            if key in value:
                parts.append((key, value[key]))
        return tuple(parts) if parts else tuple(sorted(value.items()))
    if isinstance(value, list):
        return tuple(_payload_key(item) for item in value)
    return value


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

    if insight.insight_type == InsightType.SYMPTOM_CLUSTER and isinstance(insight.payload, dict):
        method = insight.payload.get("method")
        if method == "lag":
            feature = insight.payload.get("feature")
            feature_key = feature.get("key") if isinstance(feature, dict) else None
            feature_id = feature.get("id") if isinstance(feature, dict) else None
            return (
                "symptom_cluster",
                "lag",
                _payload_key(insight.payload.get("target")),
                _payload_key(feature_key or feature_id),
                insight.payload.get("lag_days"),
            )
        if method == "lasso":
            return ("symptom_cluster", "lasso", _payload_key(insight.payload.get("target")))

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
    return {row[0]: row[1] for row in result.all()}


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


async def get_insight_by_id(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    insight_id: uuid.UUID,
) -> Insight:
    result = await db.execute(
        select(Insight).where(Insight.id == insight_id, Insight.user_id == user_id)
    )
    insight = result.scalar_one_or_none()
    if insight is None:
        raise InsightNotFoundError(insight_id)
    return insight


async def _resolve_tag_slug(db: AsyncSession, insight: Insight) -> str | None:
    payload = insight.payload if isinstance(insight.payload, dict) else {}
    tag_slug = payload.get("tag_slug")
    if isinstance(tag_slug, str) and tag_slug:
        return tag_slug
    if insight.subject_id is None:
        return None
    result = await db.execute(select(Tag.slug).where(Tag.id == insight.subject_id))
    return result.scalar_one_or_none()


async def _resolve_symptom_slug(db: AsyncSession, insight: Insight) -> str | None:
    payload = insight.payload if isinstance(insight.payload, dict) else {}
    for key in ("symptom_slug", "slug"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
    if insight.subject_id is None:
        return None
    from app.models.symptom import Symptom

    result = await db.execute(select(Symptom.slug).where(Symptom.id == insight.subject_id))
    return result.scalar_one_or_none()


async def get_insight_event_windows(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    insight_id: uuid.UUID,
    range_: TagCooccurrenceRange,
) -> InsightEventWindowsResponse:
    insight = await get_insight_by_id(db, user_id=user_id, insight_id=insight_id)
    if insight.subject_type not in {"tag", "symptom"}:
        raise InsightEventWindowsUnsupportedError(insight.subject_type)

    from datetime import UTC, date, datetime

    as_of = datetime.now(UTC).date()
    start_date, end_date = _cooccurrence_window(range_, as_of)
    label = insight.subject_label
    dates: list[date]

    if not await _analytics_enabled(db, user_id=user_id):
        return InsightEventWindowsResponse(
            range=range_,
            start_date=start_date,
            end_date=end_date,
            events=[],
            points=[],
        )

    if insight.subject_type == "tag":
        tag_slug = await _resolve_tag_slug(db, insight)
        if not tag_slug:
            dates = []
        else:
            dates = await list_historical_tag_presence_dates_by_slug(
                db,
                user_id=user_id,
                tag_slug=tag_slug,
                start_date=start_date,
                end_date=end_date,
            )
    else:
        symptom_slug = await _resolve_symptom_slug(db, insight)
        dates = await list_symptom_presence_dates(
            db,
            user_id=user_id,
            symptom_id=insight.subject_id,
            symptom_slug=symptom_slug,
            start_date=start_date,
            end_date=end_date,
        )

    timeseries = await get_timeseries(
        db,
        user_id=user_id,
        range_=cooccurrence_range_to_timeseries(range_),
    )
    events = [InsightEventWindow(onset=day, label=label) for day in dates]
    return InsightEventWindowsResponse(
        range=range_,
        start_date=start_date,
        end_date=end_date,
        events=events,
        points=timeseries.points,
    )
