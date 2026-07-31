"""Read-only service helpers for M3 insights."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import date as date_type

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
from app.services.tag_service import visible_tag_predicate

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


async def _analytics_excluded_tag_keys(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> tuple[set[uuid.UUID], set[str]]:
    """Return tag IDs and slugs excluded from analytics display.

    Includes curated default IDs that share a slug with a user override where
    ``include_in_analytics`` is False, so legacy insights linked to the default
    row are filtered too.
    """

    result = await db.execute(
        select(Tag.id, Tag.slug).where(
            visible_tag_predicate(user_id),
            Tag.include_in_analytics.is_(False),
        )
    )
    excluded_ids: set[uuid.UUID] = set()
    excluded_slugs: set[str] = set()
    for tag_id, slug in result.all():
        excluded_ids.add(tag_id)
        excluded_slugs.add(slug.casefold())

    if not excluded_slugs:
        return excluded_ids, excluded_slugs

    defaults = await db.execute(
        select(Tag.id, Tag.slug).where(
            Tag.is_default.is_(True),
            Tag.slug.in_(excluded_slugs),
        )
    )
    for tag_id, slug in defaults.all():
        excluded_ids.add(tag_id)
        excluded_slugs.add(slug.casefold())
    return excluded_ids, excluded_slugs


def _insight_excluded_by_analytics_flag(
    insight: Insight,
    *,
    excluded_ids: set[uuid.UUID],
    excluded_slugs: set[str],
) -> bool:
    """True when a tag-subject insight should be hidden from analytics feeds."""

    if insight.subject_type != "tag":
        return False
    if insight.subject_id is not None and insight.subject_id in excluded_ids:
        return True
    payload = insight.payload if isinstance(insight.payload, dict) else {}
    tag_slug = payload.get("tag_slug")
    if isinstance(tag_slug, str) and tag_slug.casefold() in excluded_slugs:
        return True
    return False


async def _filter_analytics_excluded_insights(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    insights: list[Insight],
) -> list[Insight]:
    if not insights:
        return insights
    excluded_ids, excluded_slugs = await _analytics_excluded_tag_keys(db, user_id=user_id)
    if not excluded_ids and not excluded_slugs:
        return insights
    return [
        insight
        for insight in insights
        if not _insight_excluded_by_analytics_flag(
            insight,
            excluded_ids=excluded_ids,
            excluded_slugs=excluded_slugs,
        )
    ]


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
    """Return newest insight rows for a user.

    Tag subjects with ``include_in_analytics=False`` are omitted so excluded
    habits (e.g. medication) stay out of the feed without deleting rows.
    """

    limit = _clamp_limit(limit, default=DEFAULT_INSIGHT_LIST_LIMIT, maximum=MAX_INSIGHT_LIST_LIMIT)
    # Over-fetch so filtering excluded tag subjects still fills ``limit``.
    fetch_limit = min(MAX_INSIGHT_LIST_LIMIT, max(limit * 3, limit))
    result = await db.execute(
        select(Insight)
        .where(Insight.user_id == user_id)
        .order_by(Insight.generated_at.desc(), Insight.created_at.desc())
        .limit(fetch_limit)
    )
    insights = await _filter_analytics_excluded_insights(
        db,
        user_id=user_id,
        insights=list(result.scalars().all()),
    )
    return insights[:limit]


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


def _jsonable_subject_part(value: object) -> object:
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, tuple):
        return [_jsonable_subject_part(item) for item in value]
    if isinstance(value, list):
        return [_jsonable_subject_part(item) for item in value]
    if isinstance(value, dict):
        return {
            str(key): _jsonable_subject_part(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    return value


def insight_subject_key(
    insight: Insight,
    *,
    tag_slugs_by_id: dict[uuid.UUID, str] | None = None,
) -> str:
    """Stable string key for subject-stable dismissals (#601 Phase 1).

    Matches the dedupe identity used by :func:`list_latest_insights`
    (insight family + metric + subject).
    """

    slugs = tag_slugs_by_id if tag_slugs_by_id is not None else {}
    insight_type = (
        insight.insight_type.value
        if isinstance(insight.insight_type, InsightType)
        else str(insight.insight_type)
    )
    payload = {
        "insight_type": insight_type,
        "metric": _latest_metric_key(insight),
        "subject_type": insight.subject_type,
        "subject": _jsonable_subject_part(
            _latest_subject_key(insight, tag_slugs_by_id=slugs)
        ),
    }
    return json.dumps(payload, separators=(",", ":"), sort_keys=True, ensure_ascii=True)


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
    insights = await _filter_analytics_excluded_insights(
        db,
        user_id=user_id,
        insights=insights,
    )
    from app.services.insight_dismissal_service import (
        dismissed_uuid_keys_remaining,
        list_dismissed_subject_keys,
        migrate_uuid_prefs_to_subject_dismissals,
    )

    await migrate_uuid_prefs_to_subject_dismissals(db, user_id=user_id)
    dismissed_subject_keys = await list_dismissed_subject_keys(db, user_id=user_id)
    dismissed_uuid_keys = await dismissed_uuid_keys_remaining(db, user_id=user_id)
    tag_slugs_by_id = await _tag_slugs_for_legacy_insights(db, insights)

    latest: list[Insight] = []
    seen: set[tuple[object, ...]] = set()
    for insight in insights:
        if str(insight.id) in dismissed_uuid_keys:
            continue
        subject_key = insight_subject_key(insight, tag_slugs_by_id=tag_slugs_by_id)
        if subject_key in dismissed_subject_keys:
            continue
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


@dataclass(frozen=True)
class InsightHistoryEntry:
    insight: Insight
    subject_key: str
    visibility: str  # "active" | "dismissed"
    first_seen_on: date_type | None
    last_seen_on: date_type | None
    observation_count: int


async def list_insight_history(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    status: str = "all",
    from_date: date_type | None = None,
    to_date: date_type | None = None,
    limit: int = DEFAULT_INSIGHT_LIST_LIMIT,
    offset: int = 0,
) -> tuple[list[InsightHistoryEntry], int]:
    """Return chronological insight history for the timeline (#601 Phase 2).

    Includes active and/or dismissed subjects. Does **not** subject-dedupe —
    each ``generated_for_date`` version remains visible so pattern evolution
    is queryable until account deletion.
    """

    from app.services.insight_dismissal_service import (
        dismissed_uuid_keys_remaining,
        list_dismissed_subject_keys,
        migrate_uuid_prefs_to_subject_dismissals,
    )

    if status not in {"active", "dismissed", "all"}:
        status = "all"
    limit = _clamp_limit(limit, default=DEFAULT_INSIGHT_LIST_LIMIT, maximum=MAX_INSIGHT_LIST_LIMIT)
    offset = max(0, offset)

    filters = [Insight.user_id == user_id]
    if from_date is not None:
        filters.append(Insight.generated_for_date >= from_date)
    if to_date is not None:
        filters.append(Insight.generated_for_date <= to_date)

    result = await db.execute(
        select(Insight)
        .where(*filters)
        .order_by(
            Insight.generated_for_date.desc(),
            Insight.generated_at.desc(),
            Insight.created_at.desc(),
        )
        .limit(MAX_INSIGHT_LIST_LIMIT)
    )
    insights = await _filter_analytics_excluded_insights(
        db,
        user_id=user_id,
        insights=list(result.scalars().all()),
    )

    await migrate_uuid_prefs_to_subject_dismissals(db, user_id=user_id)
    dismissed_subject_keys = await list_dismissed_subject_keys(db, user_id=user_id)
    dismissed_uuid_keys = await dismissed_uuid_keys_remaining(db, user_id=user_id)
    tag_slugs_by_id = await _tag_slugs_for_legacy_insights(db, insights)

    subject_dates: dict[str, list[date_type]] = {}
    annotated: list[tuple[Insight, str, str]] = []
    for insight in insights:
        subject_key = insight_subject_key(insight, tag_slugs_by_id=tag_slugs_by_id)
        is_dismissed = (
            subject_key in dismissed_subject_keys or str(insight.id) in dismissed_uuid_keys
        )
        visibility = "dismissed" if is_dismissed else "active"
        if status == "active" and visibility != "active":
            continue
        if status == "dismissed" and visibility != "dismissed":
            continue
        annotated.append((insight, subject_key, visibility))
        subject_dates.setdefault(subject_key, []).append(insight.generated_for_date)

    subject_stats = {
        key: (min(dates), max(dates), len(dates)) for key, dates in subject_dates.items()
    }

    total = len(annotated)
    page = annotated[offset : offset + limit]
    entries = [
        InsightHistoryEntry(
            insight=insight,
            subject_key=subject_key,
            visibility=visibility,
            first_seen_on=subject_stats[subject_key][0],
            last_seen_on=subject_stats[subject_key][1],
            observation_count=subject_stats[subject_key][2],
        )
        for insight, subject_key, visibility in page
    ]
    return entries, total


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


def _lag_onset_feature(insight: Insight) -> tuple[dict[str, object], int] | None:
    """For a lag insight, return (feature payload, lag_days); else None.

    #488: lag windows align on the *feature* (antecedent) occurrences rather
    than the insight subject (which is the outcome/target), and mark the
    outcome at t = +lag_days.
    """
    payload = insight.payload if isinstance(insight.payload, dict) else {}
    if payload.get("method") != "lag":
        return None
    feature = payload.get("feature")
    lag_days = payload.get("lag_days")
    if not isinstance(feature, dict) or not isinstance(lag_days, int):
        return None
    return feature, lag_days


async def _tag_slug_by_id(db: AsyncSession, tag_id: object) -> str | None:
    parsed = _parse_uuid(tag_id)
    if parsed is None:
        return None
    result = await db.execute(select(Tag.slug).where(Tag.id == parsed))
    return result.scalar_one_or_none()


def _parse_uuid(value: object) -> uuid.UUID | None:
    if isinstance(value, uuid.UUID):
        return value
    if isinstance(value, str):
        try:
            return uuid.UUID(value)
        except ValueError:
            return None
    return None


async def get_insight_event_windows(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    insight_id: uuid.UUID,
    range_: TagCooccurrenceRange,
) -> InsightEventWindowsResponse:
    insight = await get_insight_by_id(db, user_id=user_id, insight_id=insight_id)

    # Lag insights align on the feature (antecedent); everything else on the subject.
    lag = _lag_onset_feature(insight)
    onset_slug: str | None
    label: str | None
    onset_id: object
    if lag is not None:
        feature, lag_days = lag
        onset_kind = feature.get("kind")
        raw_slug = feature.get("slug")
        onset_slug = raw_slug if isinstance(raw_slug, str) else None
        onset_id = feature.get("id")
        raw_name = feature.get("name")
        label = raw_name if isinstance(raw_name, str) else None
    else:
        onset_kind = insight.subject_type
        onset_slug = None
        onset_id = insight.subject_id
        label = insight.subject_label
        lag_days = None

    if onset_kind not in {"tag", "symptom"}:
        raise InsightEventWindowsUnsupportedError(str(onset_kind))

    from datetime import UTC, date, datetime

    as_of = datetime.now(UTC).date()
    start_date, end_date = _cooccurrence_window(range_, as_of)
    dates: list[date]

    if not await _analytics_enabled(db, user_id=user_id):
        return InsightEventWindowsResponse(
            range=range_,
            start_date=start_date,
            end_date=end_date,
            events=[],
            points=[],
            lag_days=lag_days,
        )

    if onset_kind == "tag":
        tag_slug = onset_slug if lag is not None else await _resolve_tag_slug(db, insight)
        if not tag_slug and lag is not None:
            tag_slug = await _tag_slug_by_id(db, onset_id)
        # Lag insights carry the tag as payload.feature, so the insight itself is
        # not subject-filtered by list_insights. Enforce the analytics-exclusion
        # promise here before surfacing an excluded tag's presence dates.
        if tag_slug and lag is not None:
            excluded_ids, excluded_slugs = await _analytics_excluded_tag_keys(db, user_id=user_id)
            if tag_slug.casefold() in excluded_slugs or _parse_uuid(onset_id) in excluded_ids:
                tag_slug = None
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
        symptom_id = _parse_uuid(onset_id) if lag is not None else insight.subject_id
        symptom_slug = onset_slug if lag is not None else await _resolve_symptom_slug(db, insight)
        dates = await list_symptom_presence_dates(
            db,
            user_id=user_id,
            symptom_id=symptom_id,
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
        lag_days=lag_days,
    )
