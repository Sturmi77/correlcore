"""Backfill ``lag_profile`` on persisted lag insights (#488 Phase 1b).

Older rows may carry ``method=lag`` and ``lag_days`` without the ``lag_profile``
series the UI needs for mini-bars and the lag heatmap. The profile cannot be
reconstructed from the stored payload alone — it is recomputed from the user's
entry history via the same lag analysis pipeline used at generation time.
"""

from __future__ import annotations

import logging
import uuid
from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import reset_current_user_dek, set_current_user_dek, unwrap_dek
from app.db.session import bind_rls_current_user
from app.models.insight import Insight
from app.models.user import User
from app.models.user_encryption_key import UserEncryptionKey
from app.services.insight_engine import generate_insight_candidates, load_analytics_data
from app.services.stats_service import _analytics_enabled

logger = logging.getLogger(__name__)

MIN_USABLE_LAG_PROFILE_POINTS = 2

LagProfileSeries = list[dict[str, float | int]]
PairKey = tuple[tuple[str, str], tuple[str, str]]


@dataclass(frozen=True)
class LagInsightRow:
    """Minimal insight projection for backfill — avoids loading ``statement_enc``."""

    id: uuid.UUID
    user_id: uuid.UUID
    payload: dict[str, Any]
    generated_for_date: date


@dataclass
class LagProfileBackfillSummary:
    users_processed: int = 0
    insights_scanned: int = 0
    insights_updated: int = 0
    insights_skipped: int = 0
    insights_unmatched: int = 0
    user_ids: list[uuid.UUID] = field(default_factory=list)


def payload_needs_lag_profile(payload: Mapping[str, Any] | None) -> bool:
    """Return True when a lag insight payload is missing a usable profile series."""

    if not payload or payload.get("method") != "lag":
        return False
    raw = payload.get("lag_profile")
    if not isinstance(raw, list):
        return True
    valid_points = sum(
        1
        for point in raw
        if isinstance(point, dict)
        and isinstance(point.get("lag"), int)
        and isinstance(point.get("r"), (int, float))
    )
    return valid_points < MIN_USABLE_LAG_PROFILE_POINTS


def _side_key(side: object) -> tuple[str, str]:
    if not isinstance(side, dict):
        return ("", "")

    kind = side.get("kind")
    kind_token = kind if isinstance(kind, str) else ""

    for attr in ("key", "slug", "id", "name"):
        value = side.get(attr)
        if isinstance(value, str) and value:
            token = value.casefold()
            if attr == "key" and ":" in token:
                token = token.split(":", 1)[1]
            return (kind_token, token)

    return (kind_token, "")


def pair_key_from_payload(payload: Mapping[str, Any]) -> PairKey:
    """Canonical (target, feature) key shared by insight rows and lag candidates."""

    return (_side_key(payload.get("target")), _side_key(payload.get("feature")))


def build_profile_lookup_from_candidates(
    candidates: Iterable[Any],
) -> dict[PairKey, LagProfileSeries]:
    """Map feature/target pairs to ``lag_profile`` from lag insight candidates."""

    lookup: dict[PairKey, LagProfileSeries] = {}
    for candidate in candidates:
        payload = candidate.payload
        if not isinstance(payload, dict) or payload.get("method") != "lag":
            continue
        profile = payload.get("lag_profile")
        if not isinstance(profile, list) or len(profile) < MIN_USABLE_LAG_PROFILE_POINTS:
            continue
        lookup[pair_key_from_payload(payload)] = profile
    return lookup


def build_backfilled_payload(
    payload: Mapping[str, Any],
    profile_lookup: Mapping[PairKey, LagProfileSeries],
) -> dict[str, Any] | None:
    """Return an updated payload when a matching ``lag_profile`` exists."""

    if not payload_needs_lag_profile(payload):
        return None

    profile = profile_lookup.get(pair_key_from_payload(payload))
    if profile is None:
        return None

    updated = dict(payload)
    updated["lag_profile"] = list(profile)
    return updated


def apply_lag_profile_backfill(
    insight: Insight,
    profile_lookup: Mapping[PairKey, LagProfileSeries],
) -> bool:
    """Attach ``lag_profile`` to an in-memory ``Insight`` (tests / legacy callers)."""

    payload = insight.payload if isinstance(insight.payload, dict) else None
    updated = build_backfilled_payload(payload or {}, profile_lookup)
    if updated is None:
        return False
    insight.payload = updated
    return True


async def _list_backfill_user_ids(
    db: AsyncSession,
    *,
    user_id: uuid.UUID | None,
) -> list[uuid.UUID]:
    if user_id is not None:
        return [user_id]
    result = await db.execute(
        select(User.id).where(User.is_active.is_(True), User.is_verified.is_(True))
    )
    return list(result.scalars().all())


async def _lag_insights_needing_backfill(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> list[LagInsightRow]:
    """Load lag insights missing profiles for one user (requires RLS context)."""

    stmt = (
        select(Insight.id, Insight.user_id, Insight.payload, Insight.generated_for_date)
        .where(
            Insight.user_id == user_id,
            Insight.payload["method"].astext == "lag",
        )
        .order_by(Insight.generated_for_date.desc())
    )
    result = await db.execute(stmt)
    rows: list[LagInsightRow] = []
    for insight_id, owner_id, payload, generated_for_date in result.all():
        if not isinstance(payload, dict):
            continue
        if not payload_needs_lag_profile(payload):
            continue
        if generated_for_date is None:
            generated_for_date = datetime.now(UTC).date()
        rows.append(
            LagInsightRow(
                id=insight_id,
                user_id=owner_id,
                payload=payload,
                generated_for_date=generated_for_date,
            )
        )
    return rows


async def _backfill_lag_profiles_for_user(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    summary: LagProfileBackfillSummary,
) -> None:
    await bind_rls_current_user(db, user_id=user_id)
    user_insights = await _lag_insights_needing_backfill(db, user_id=user_id)
    if not user_insights:
        return

    summary.insights_scanned += len(user_insights)

    if not await _analytics_enabled(db, user_id=user_id):
        summary.insights_skipped += len(user_insights)
        logger.info(
            "Skipping user %s: analytics disabled (%s lag insight(s))",
            user_id,
            len(user_insights),
        )
        return

    key_result = await db.execute(
        select(UserEncryptionKey.wrapped_dek).where(UserEncryptionKey.user_id == user_id)
    )
    wrapped_dek = key_result.scalar_one_or_none()
    if wrapped_dek is None:
        summary.insights_skipped += len(user_insights)
        logger.warning(
            "Skipping user %s: no encryption key (%s lag insight(s))",
            user_id,
            len(user_insights),
        )
        return

    dek_token = set_current_user_dek(user_id, unwrap_dek(wrapped_dek))
    updated_for_user = 0
    unmatched_for_user = 0

    try:
        by_cutoff: dict[date, list[LagInsightRow]] = defaultdict(list)
        for insight in user_insights:
            by_cutoff[insight.generated_for_date].append(insight)

        for generated_for_date, batch in by_cutoff.items():
            analysis_as_of = generated_for_date + timedelta(days=1)
            entries, tags, symptoms = await load_analytics_data(
                db,
                user_id=user_id,
                as_of=analysis_as_of,
            )
            if not entries:
                unmatched_for_user += len(batch)
                continue

            candidates = generate_insight_candidates(
                entries,
                tags,
                symptoms,
                as_of=analysis_as_of,
            )
            profile_lookup = build_profile_lookup_from_candidates(candidates)

            for insight in batch:
                updated_payload = build_backfilled_payload(insight.payload, profile_lookup)
                if updated_payload is None:
                    unmatched_for_user += 1
                    continue
                await db.execute(
                    update(Insight).where(Insight.id == insight.id).values(payload=updated_payload)
                )
                updated_for_user += 1
    finally:
        reset_current_user_dek(dek_token)

    if updated_for_user or unmatched_for_user:
        summary.users_processed += 1
        summary.user_ids.append(user_id)
    summary.insights_updated += updated_for_user
    summary.insights_unmatched += unmatched_for_user

    if updated_for_user or unmatched_for_user:
        logger.info(
            "User %s: updated %s/%s lag insight(s); %s unmatched",
            user_id,
            updated_for_user,
            len(user_insights),
            unmatched_for_user,
        )


async def backfill_lag_profiles(
    db: AsyncSession,
    *,
    user_id: uuid.UUID | None = None,
    as_of: date | None = None,
) -> LagProfileBackfillSummary:
    """Recompute and attach ``lag_profile`` for persisted lag insights.

    When ``user_id`` is omitted, iterates active verified users and binds RLS +
    DEK per user so production ``correlcore_app`` role sees rows under FORCE RLS.

    ``as_of`` is deprecated: each insight uses its own ``generated_for_date`` cutoff.
    """

    if as_of is not None:
        logger.warning(
            "backfill_lag_profiles(as_of=...) is deprecated; using per-insight generated_for_date"
        )

    summary = LagProfileBackfillSummary()
    user_ids = await _list_backfill_user_ids(db, user_id=user_id)

    for current_user_id in user_ids:
        await _backfill_lag_profiles_for_user(db, user_id=current_user_id, summary=summary)

    return summary
