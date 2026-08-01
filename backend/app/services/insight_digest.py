"""Weekly insight digest ranking and push-safe payload builders (#147)."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from datetime import date as date_type

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.insight import Insight, InsightTier
from app.models.insight_digest import InsightDigest
from app.models.user_preference import UserPreference

DIGEST_WINDOW_DAYS = 7
DIGEST_TOP_N = 3
MIN_DIGEST_CONFIDENCE = 0.55

_HEALTH_TERMS = re.compile(
    r"\b(mood|energy|stress|symptom|headache|fatigue|pain|sleep|anxiety|depression)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class DigestInsightItem:
    """One ranked insight included in a weekly digest."""

    id: uuid.UUID
    insight_type: str
    metric: str
    effect_size: float | None
    confidence: float | None
    statement: str | None


@dataclass(frozen=True)
class WeeklyDigest:
    """Computed weekly digest for one user."""

    week_start: date_type
    week_end: date_type
    insights: tuple[DigestInsightItem, ...]

    @property
    def insight_count(self) -> int:
        return len(self.insights)


class DigestNotAvailableError(Exception):
    """Raised when fewer than three qualifying insights exist."""


class DigestDisabledError(Exception):
    """Raised when the user opted out of weekly digests."""


def insight_has_sufficient_confidence(insight: Insight) -> bool:
    """Return True when an insight meets digest inclusion gates."""

    if insight.tier in {InsightTier.NONE, InsightTier.EARLY}:
        return False
    if insight.confidence is None:
        return False
    return insight.confidence >= MIN_DIGEST_CONFIDENCE


def rank_digest_insights(insights: list[Insight]) -> list[Insight]:
    """Rank insights by absolute effect size and return the top three."""

    qualified = [insight for insight in insights if insight_has_sufficient_confidence(insight)]
    ranked = sorted(
        qualified,
        key=lambda item: (
            -abs(item.effect_size or 0.0),
            -(item.confidence or 0.0),
            item.generated_at,
        ),
    )
    return ranked[:DIGEST_TOP_N]


def build_weekly_digest(
    insights: list[Insight],
    *,
    week_start: date_type,
    week_end: date_type,
) -> WeeklyDigest | None:
    """Build a digest or return None when fewer than three insights qualify."""

    ranked = rank_digest_insights(insights)
    if len(ranked) < DIGEST_TOP_N:
        return None

    items = tuple(_insight_to_digest_item(insight) for insight in ranked)
    return WeeklyDigest(week_start=week_start, week_end=week_end, insights=items)


def build_push_payload(digest: WeeklyDigest) -> dict[str, str]:
    """Return generic push notification copy without health-specific data."""

    count = digest.insight_count
    noun = "pattern" if count == 1 else "patterns"
    return {
        "title": "Your weekly insight digest",
        "body": f"Review {count} {noun} from your journal this week.",
    }


def push_payload_is_scrubbed(payload: dict[str, str], *, statements: list[str]) -> bool:
    """Return True when push copy contains no health terms from source statements."""

    combined = f"{payload.get('title', '')} {payload.get('body', '')}"
    if _HEALTH_TERMS.search(combined):
        return False
    for statement in statements:
        if statement and statement in combined:
            return False
    return True


def digest_window(as_of: datetime | None = None) -> tuple[date_type, date_type]:
    """Return the inclusive digest window ending on the reference date."""

    current = (as_of or datetime.now(UTC)).date()
    week_end = current
    week_start = current - timedelta(days=DIGEST_WINDOW_DAYS - 1)
    return week_start, week_end


async def _digest_enabled(db: AsyncSession, *, user_id: uuid.UUID) -> bool:
    """Opt-in only: missing preference row or explicit false → disabled."""
    result = await db.execute(
        select(UserPreference.digest_enabled).where(UserPreference.user_id == user_id)
    )
    enabled = result.scalar_one_or_none()
    return enabled is True


async def load_recent_insights(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    week_start: date_type,
    week_end: date_type,
) -> list[Insight]:
    window_start = datetime.combine(week_start, datetime.min.time(), tzinfo=UTC)
    window_end = datetime.combine(week_end, datetime.max.time(), tzinfo=UTC)
    result = await db.execute(
        select(Insight)
        .where(
            Insight.user_id == user_id,
            Insight.generated_at >= window_start,
            Insight.generated_at <= window_end,
        )
        .order_by(Insight.generated_at.desc())
    )
    return list(result.scalars().all())


def _insight_to_digest_item(insight: Insight) -> DigestInsightItem:
    return DigestInsightItem(
        id=insight.id,
        insight_type=insight.insight_type.value,
        metric=insight.metric,
        effect_size=insight.effect_size,
        confidence=insight.confidence,
        statement=insight.statement_enc,
    )


async def load_latest_stored_digest(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> InsightDigest | None:
    """Return the newest persisted digest row for ``user_id``, if any."""

    result = await db.execute(
        select(InsightDigest)
        .where(InsightDigest.user_id == user_id)
        .order_by(InsightDigest.generated_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def hydrate_stored_digest(
    db: AsyncSession,
    *,
    row: InsightDigest,
) -> WeeklyDigest | None:
    """Rebuild a :class:`WeeklyDigest` from a stored row + live insight rows.

    Returns ``None`` when insight IDs are missing/deleted so callers can fall
    back to a fresh compute. Dismissed subjects are dropped from the returned
    envelope without mutating the persisted snapshot (#601).
    """

    try:
        ordered_ids = [uuid.UUID(str(raw)) for raw in row.insight_ids]
    except (TypeError, ValueError):
        return None
    if len(ordered_ids) < DIGEST_TOP_N:
        return None

    result = await db.execute(
        select(Insight).where(
            Insight.user_id == row.user_id,
            Insight.id.in_(ordered_ids),
        )
    )
    by_id = {insight.id: insight for insight in result.scalars().all()}
    items: list[DigestInsightItem] = []
    for insight_id in ordered_ids:
        insight = by_id.get(insight_id)
        if insight is None:
            return None
        items.append(_insight_to_digest_item(insight))

    digest = WeeklyDigest(
        week_start=row.week_start,
        week_end=row.week_end,
        insights=tuple(items),
    )
    return await _filter_digest_dismissals(db, user_id=row.user_id, digest=digest)


async def _filter_digest_dismissals(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    digest: WeeklyDigest,
) -> WeeklyDigest:
    """Drop currently dismissed insights from a digest response (snapshot untouched)."""

    from app.services.insight_dismissal_service import (
        dismissed_uuid_keys_remaining,
        list_dismissed_subject_keys,
        migrate_uuid_prefs_to_subject_dismissals,
    )
    from app.services.insight_service import (
        _tag_slugs_for_legacy_insights,
        insight_subject_key,
    )

    await migrate_uuid_prefs_to_subject_dismissals(db, user_id=user_id)
    dismissed_subject_keys = await list_dismissed_subject_keys(db, user_id=user_id)
    dismissed_uuid_keys = await dismissed_uuid_keys_remaining(db, user_id=user_id)
    if not dismissed_subject_keys and not dismissed_uuid_keys:
        return digest

    insight_ids = [item.id for item in digest.insights]
    result = await db.execute(
        select(Insight).where(Insight.user_id == user_id, Insight.id.in_(insight_ids))
    )
    by_id = {insight.id: insight for insight in result.scalars().all()}
    tag_slugs_by_id = await _tag_slugs_for_legacy_insights(db, list(by_id.values()))

    kept: list[DigestInsightItem] = []
    for item in digest.insights:
        if str(item.id) in dismissed_uuid_keys:
            continue
        insight = by_id.get(item.id)
        if insight is not None and (
            insight_subject_key(insight, tag_slugs_by_id=tag_slugs_by_id) in dismissed_subject_keys
        ):
            continue
        kept.append(item)

    return WeeklyDigest(
        week_start=digest.week_start,
        week_end=digest.week_end,
        insights=tuple(kept),
    )


async def compute_weekly_digest_for_user(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    as_of: datetime | None = None,
    require_enabled: bool = True,
) -> WeeklyDigest:
    """Always recompute a digest from recent insights (worker / fallback path)."""

    if require_enabled and not await _digest_enabled(db, user_id=user_id):
        raise DigestDisabledError(user_id)

    week_start, week_end = digest_window(as_of)
    insights = await load_recent_insights(
        db,
        user_id=user_id,
        week_start=week_start,
        week_end=week_end,
    )
    from app.services.insight_dismissal_service import (
        dismissed_uuid_keys_remaining,
        list_dismissed_subject_keys,
        migrate_uuid_prefs_to_subject_dismissals,
    )
    from app.services.insight_service import (
        _tag_slugs_for_legacy_insights,
        insight_subject_key,
    )

    await migrate_uuid_prefs_to_subject_dismissals(db, user_id=user_id)
    dismissed_subject_keys = await list_dismissed_subject_keys(db, user_id=user_id)
    dismissed_uuid_keys = await dismissed_uuid_keys_remaining(db, user_id=user_id)
    if dismissed_subject_keys or dismissed_uuid_keys:
        tag_slugs_by_id = await _tag_slugs_for_legacy_insights(db, insights)
        filtered: list[Insight] = []
        for insight in insights:
            if str(insight.id) in dismissed_uuid_keys:
                continue
            if (
                insight_subject_key(insight, tag_slugs_by_id=tag_slugs_by_id)
                in dismissed_subject_keys
            ):
                continue
            filtered.append(insight)
        insights = filtered
    digest = build_weekly_digest(insights, week_start=week_start, week_end=week_end)
    if digest is None:
        raise DigestNotAvailableError(user_id)
    return digest


async def get_latest_weekly_digest(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    as_of: datetime | None = None,
) -> WeeklyDigest:
    """Return the latest weekly digest for one user.

    Prefers a persisted ``insight_digests`` snapshot (hydrated from insight
    rows). Falls back to recomputing when nothing is stored or hydration fails.
    """

    if not await _digest_enabled(db, user_id=user_id):
        raise DigestDisabledError(user_id)

    stored = await load_latest_stored_digest(db, user_id=user_id)
    if stored is not None:
        hydrated = await hydrate_stored_digest(db, row=stored)
        if hydrated is not None:
            return hydrated

    return await compute_weekly_digest_for_user(
        db,
        user_id=user_id,
        as_of=as_of,
        require_enabled=False,
    )


async def store_weekly_digest(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    digest: WeeklyDigest,
) -> InsightDigest:
    """Persist a digest snapshot for later GET (and future push delivery)."""

    push = build_push_payload(digest)
    row = InsightDigest(
        user_id=user_id,
        week_start=digest.week_start,
        week_end=digest.week_end,
        insight_ids=[str(item.id) for item in digest.insights],
        insight_count=digest.insight_count,
        push_title=push["title"],
        push_body=push["body"],
    )
    db.add(row)
    await db.flush()
    await db.refresh(row)
    return row
