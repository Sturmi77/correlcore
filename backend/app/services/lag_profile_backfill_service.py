"""Backfill ``lag_profile`` on persisted lag insights (#488 Phase 1b).

Older rows may carry ``method=lag`` and ``lag_days`` without the ``lag_profile``
series the UI needs for mini-bars and the lag heatmap. The profile cannot be
reconstructed from the stored payload alone — it is recomputed from the user's
entry history via the same lag analysis pipeline used at generation time.
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.insight import Insight
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


async def _lag_insights_needing_backfill(
    db: AsyncSession,
    *,
    user_id: uuid.UUID | None,
) -> list[LagInsightRow]:
    # Project id/user_id/payload only — ``statement_enc`` needs a bound DEK.
    stmt = select(Insight.id, Insight.user_id, Insight.payload).where(
        Insight.payload["method"].astext == "lag"
    )
    if user_id is not None:
        stmt = stmt.where(Insight.user_id == user_id)
    stmt = stmt.order_by(Insight.user_id.asc(), Insight.generated_at.desc())
    result = await db.execute(stmt)
    rows: list[LagInsightRow] = []
    for insight_id, owner_id, payload in result.all():
        if not isinstance(payload, dict):
            continue
        if payload_needs_lag_profile(payload):
            rows.append(LagInsightRow(id=insight_id, user_id=owner_id, payload=payload))
    return rows


async def backfill_lag_profiles(
    db: AsyncSession,
    *,
    user_id: uuid.UUID | None = None,
    as_of: date | None = None,
) -> LagProfileBackfillSummary:
    """Recompute and attach ``lag_profile`` for persisted lag insights."""

    summary = LagProfileBackfillSummary()
    insights = await _lag_insights_needing_backfill(db, user_id=user_id)
    summary.insights_scanned = len(insights)
    if not insights:
        return summary

    grouped: dict[uuid.UUID, list[LagInsightRow]] = {}
    for insight in insights:
        grouped.setdefault(insight.user_id, []).append(insight)

    analysis_as_of = as_of or (datetime.now(UTC).date() + timedelta(days=1))

    for current_user_id, user_insights in grouped.items():
        if not await _analytics_enabled(db, user_id=current_user_id):
            summary.insights_skipped += len(user_insights)
            logger.info(
                "Skipping user %s: analytics disabled (%s lag insight(s))",
                current_user_id,
                len(user_insights),
            )
            continue

        entries, tags, symptoms = await load_analytics_data(
            db,
            user_id=current_user_id,
            as_of=analysis_as_of,
        )
        if not entries:
            summary.insights_unmatched += len(user_insights)
            logger.info(
                "No analytics entries for user %s; leaving %s lag insight(s) unchanged",
                current_user_id,
                len(user_insights),
            )
            continue

        candidates = generate_insight_candidates(
            entries,
            tags,
            symptoms,
            as_of=analysis_as_of,
        )
        profile_lookup = build_profile_lookup_from_candidates(candidates)

        updated_for_user = 0
        unmatched_for_user = 0
        for insight in user_insights:
            updated_payload = build_backfilled_payload(insight.payload, profile_lookup)
            if updated_payload is None:
                unmatched_for_user += 1
                continue
            await db.execute(
                update(Insight)
                .where(Insight.id == insight.id)
                .values(payload=updated_payload)
            )
            updated_for_user += 1

        summary.users_processed += 1
        summary.user_ids.append(current_user_id)
        summary.insights_updated += updated_for_user
        summary.insights_unmatched += unmatched_for_user
        logger.info(
            "User %s: updated %s/%s lag insight(s); %s unmatched",
            current_user_id,
            updated_for_user,
            len(user_insights),
            unmatched_for_user,
        )

    return summary
