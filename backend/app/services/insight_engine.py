"""M3 analytics insight engine.

This module computes the first deterministic insight candidates for CorrelCore.
It deliberately stays inside the service layer: no API route, scheduler changes
or UI assumptions are introduced in this sprint.
"""

from __future__ import annotations

import logging
import math
import uuid
from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from datetime import date as date_type
from typing import Any, Literal

from scipy.stats import chisquare, pointbiserialr, spearmanr
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from statsmodels.stats.multitest import multipletests

from app.core.config import settings
from app.models.entry import Entry
from app.models.insight import Insight, InsightTier, InsightType
from app.models.tag import EntryTag, Tag

logger = logging.getLogger(__name__)

EARLY_ENTRY_COUNT = 3
PRELIMINARY_ENTRY_COUNT = 8
DEVELOPING_ENTRY_COUNT = 15
ROBUST_ENTRY_COUNT = 30
MIN_WEEKDAY_ENTRIES = 7
MIN_BIVARIATE_ENTRIES = DEVELOPING_ENTRY_COUNT
MIN_TAG_GROUP_SIZE = 2
MIN_ABS_EFFECT_SIZE = 0.25
MIN_WEEKDAY_DELTA = 0.5
FDR_ALPHA = 0.05

MetricName = Literal["mood_score", "energy", "stress"]

_METRIC_LABELS: dict[MetricName, str] = {
    "mood_score": "mood",
    "energy": "energy",
    "stress": "stress",
}
_WEEKDAY_LABELS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")


@dataclass(frozen=True)
class AnalyticsEntry:
    """Daily row used by the insight engine."""

    id: uuid.UUID
    entry_date: date_type
    mood_score: int
    energy: int
    stress: int
    tag_ids: frozenset[uuid.UUID] = field(default_factory=frozenset)


@dataclass(frozen=True)
class TagSnapshot:
    """Tag metadata needed for statement rendering."""

    id: uuid.UUID
    label: str
    slug: str


@dataclass(frozen=True)
class InsightCandidate:
    """Computed, persistence-ready insight payload."""

    insight_type: InsightType
    tier: InsightTier
    metric: str
    subject_type: str | None
    subject_id: uuid.UUID | None
    subject_label: str | None
    effect_size: float | None
    confidence: float | None
    sample_n: int
    statement: str
    flags: dict[str, object]
    payload: dict[str, object]
    generated_for_date: date_type


def confidence_tier_for_sample(sample_n: int) -> InsightTier:
    """Map entry count to the M3 tiered confidence ladder."""

    if sample_n >= ROBUST_ENTRY_COUNT:
        return InsightTier.ROBUST
    if sample_n >= DEVELOPING_ENTRY_COUNT:
        return InsightTier.DEVELOPING
    if sample_n >= PRELIMINARY_ENTRY_COUNT:
        return InsightTier.PRELIMINARY
    if sample_n >= EARLY_ENTRY_COUNT:
        return InsightTier.EARLY
    return InsightTier.NONE


def _metric_value(entry: AnalyticsEntry, metric: MetricName) -> int:
    if metric == "mood_score":
        return entry.mood_score
    if metric == "energy":
        return entry.energy
    return entry.stress


def display_metric_value(metric: MetricName, raw: int, *, scale_min: int = 1, scale_max: int = 5) -> int:
    """View-layer inversion for stress (FRONTEND.md §4.3). Raw DB values stay unchanged."""

    if metric == "stress":
        return scale_min + scale_max - raw
    return raw


def _finite_float(value: Any) -> float | None:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    return numeric if math.isfinite(numeric) else None


def _round_or_none(value: float | None, digits: int = 4) -> float | None:
    if value is None:
        return None
    return round(value, digits)


def _confidence(
    effect_size: float | None, p_value: float | None, tier: InsightTier
) -> float | None:
    if effect_size is None or tier is InsightTier.NONE:
        return None

    tier_weight = {
        InsightTier.EARLY: 0.35,
        InsightTier.PRELIMINARY: 0.55,
        InsightTier.DEVELOPING: 0.75,
        InsightTier.ROBUST: 0.95,
    }.get(tier, 0.0)
    effect_weight = min(1.0, abs(effect_size) / 0.8)
    p_weight = 0.65 if p_value is None else max(0.0, min(1.0, 1.0 - p_value))
    return round(max(0.0, min(1.0, tier_weight * effect_weight * p_weight)), 2)


def _direction(effect_size: float | None, positive: str, negative: str) -> str:
    return positive if effect_size is not None and effect_size >= 0 else negative


def _base_flags(
    *,
    p_value: float | None,
    method: str,
    p_corrected: float | None = None,
) -> dict[str, object]:
    flags: dict[str, object] = {
        "method": method,
        "p_value": _round_or_none(p_value),
        "medical_disclaimer_required": True,
        "causal_claim": False,
    }
    if p_corrected is not None:
        flags["p_corrected"] = _round_or_none(p_corrected)
        flags["multiple_testing_correction"] = "fdr_bh"
    return flags


def _fdr_results(p_values: Sequence[float]) -> list[tuple[bool, float]]:
    """Apply Benjamini-Hochberg FDR correction to one correlation family."""

    if not p_values:
        return []
    reject, p_corrected, _, _ = multipletests(p_values, alpha=FDR_ALPHA, method="fdr_bh")
    return [
        (bool(sig), float(corrected)) for sig, corrected in zip(reject, p_corrected, strict=True)
    ]


def is_weekday_biased(
    entries: Sequence[AnalyticsEntry],
    tag_id: uuid.UUID,
    *,
    threshold_p: float = FDR_ALPHA,
) -> bool:
    """Return True when a tag is concentrated on specific weekdays."""

    observed = [
        sum(1 for entry in entries if tag_id in entry.tag_ids and entry.entry_date.weekday() == day)
        for day in range(7)
    ]
    total = sum(observed)
    if total < settings.ANALYTICS_MIN_TAG_USAGES:
        return False

    expected = [total / 7] * 7
    result = chisquare(observed, f_exp=expected)
    p_value = _finite_float(result.pvalue)
    return p_value is not None and p_value < threshold_p


def _weekday_confounded_statement(statement: str, *, weekday_confounded: bool) -> str:
    if not weekday_confounded:
        return statement
    return f"{statement} Note: this pattern occurs primarily on specific weekdays."


def _dedupe_daily_entries(entries: Sequence[AnalyticsEntry]) -> list[AnalyticsEntry]:
    """Collapse multiple slots on a date into one daily vector.

    M1/M2 normally have one entry per day. This keeps the engine additive for
    the existing M3 multi-slot reservation by averaging scores and unioning tags.
    """

    grouped: dict[date_type, list[AnalyticsEntry]] = defaultdict(list)
    for entry in entries:
        grouped[entry.entry_date].append(entry)

    daily: list[AnalyticsEntry] = []
    for day, rows in sorted(grouped.items()):
        first = rows[0]
        daily.append(
            AnalyticsEntry(
                id=first.id,
                entry_date=day,
                mood_score=round(sum(row.mood_score for row in rows) / len(rows)),
                energy=round(sum(row.energy for row in rows) / len(rows)),
                stress=round(sum(row.stress for row in rows) / len(rows)),
                tag_ids=frozenset(tag_id for row in rows for tag_id in row.tag_ids),
            )
        )
    return daily


def _spearman_candidates(
    entries: Sequence[AnalyticsEntry],
    *,
    tier: InsightTier,
    generated_for_date: date_type,
) -> list[InsightCandidate]:
    if len(entries) < MIN_BIVARIATE_ENTRIES:
        return []

    raw: list[tuple[MetricName, MetricName, str, float, float]] = []
    pairs: tuple[tuple[MetricName, MetricName, str], ...] = (
        ("energy", "mood_score", "energy_mood"),
        ("stress", "mood_score", "stress_mood"),
    )
    for left, right, metric in pairs:
        left_values = [_metric_value(entry, left) for entry in entries]
        right_values = [_metric_value(entry, right) for entry in entries]
        if len(set(left_values)) < 2 or len(set(right_values)) < 2:
            continue
        result = spearmanr(left_values, right_values)
        rho = _finite_float(result.statistic)
        p_value = _finite_float(result.pvalue)
        if rho is None or p_value is None or abs(rho) < MIN_ABS_EFFECT_SIZE:
            continue
        raw.append((left, right, metric, rho, p_value))

    candidates: list[InsightCandidate] = []
    for (left, right, metric, rho, p_value), (significant, p_corrected) in zip(
        raw,
        _fdr_results([item[4] for item in raw]),
        strict=True,
    ):
        if not significant:
            continue
        direction = _direction(rho, "higher", "lower")
        statement = (
            f"In your entries so far, {_METRIC_LABELS[left]} tends to be {direction} "
            f"when {_METRIC_LABELS[right]} is higher. This is a data pattern, not a diagnosis."
        )
        candidates.append(
            InsightCandidate(
                insight_type=InsightType.SPEARMAN,
                tier=tier,
                metric=metric,
                subject_type="metric",
                subject_id=None,
                subject_label=right,
                effect_size=round(rho, 4),
                confidence=_confidence(rho, p_corrected, tier),
                sample_n=len(entries),
                statement=statement,
                flags=_base_flags(p_value=p_value, p_corrected=p_corrected, method="spearman"),
                payload={
                    "left_metric": left,
                    "right_metric": right,
                    "rho": round(rho, 4),
                    "p_corrected": round(p_corrected, 4),
                },
                generated_for_date=generated_for_date,
            )
        )
    return candidates


def _pointbiserial_candidates(
    entries: Sequence[AnalyticsEntry],
    tags: dict[uuid.UUID, TagSnapshot],
    *,
    tier: InsightTier,
    generated_for_date: date_type,
) -> list[InsightCandidate]:
    if len(entries) < MIN_BIVARIATE_ENTRIES:
        return []

    raw: list[
        tuple[
            uuid.UUID,
            TagSnapshot,
            float,
            float,
            int,
            int,
            float,
            float,
            bool,
        ]
    ] = []
    for tag_id, tag in sorted(tags.items(), key=lambda item: item[1].slug):
        binary = [1 if tag_id in entry.tag_ids else 0 for entry in entries]
        tagged_count = sum(binary)
        untagged_count = len(binary) - tagged_count
        if tagged_count < settings.ANALYTICS_MIN_TAG_USAGES or untagged_count < MIN_TAG_GROUP_SIZE:
            continue

        mood_values = [entry.mood_score for entry in entries]
        result = pointbiserialr(binary, mood_values)
        coefficient = _finite_float(result.statistic)
        p_value = _finite_float(result.pvalue)
        if coefficient is None or p_value is None or abs(coefficient) < MIN_ABS_EFFECT_SIZE:
            continue

        tagged_mood = (
            sum(entry.mood_score for entry, present in zip(entries, binary, strict=True) if present)
            / tagged_count
        )
        untagged_mood = (
            sum(
                entry.mood_score
                for entry, present in zip(entries, binary, strict=True)
                if not present
            )
            / untagged_count
        )
        raw.append(
            (
                tag_id,
                tag,
                coefficient,
                p_value,
                tagged_count,
                untagged_count,
                tagged_mood,
                untagged_mood,
                is_weekday_biased(entries, tag_id),
            )
        )

    candidates: list[InsightCandidate] = []
    for (
        tag_id,
        tag,
        coefficient,
        p_value,
        tagged_count,
        untagged_count,
        tagged_mood,
        untagged_mood,
        weekday_confounded,
    ), (significant, p_corrected) in zip(
        raw,
        _fdr_results([item[3] for item in raw]),
        strict=True,
    ):
        if not significant:
            continue
        direction = _direction(coefficient, "higher", "lower")
        statement = (
            f"Days tagged {tag.label} currently line up with {direction} mood scores "
            "in your data. Treat this as a pattern to reflect on, not a cause."
        )
        statement = _weekday_confounded_statement(
            statement,
            weekday_confounded=weekday_confounded,
        )
        candidates.append(
            InsightCandidate(
                insight_type=InsightType.POINTBISERIAL,
                tier=tier,
                metric="mood_score",
                subject_type="tag",
                subject_id=tag_id,
                subject_label=tag.label,
                effect_size=round(coefficient, 4),
                confidence=_confidence(coefficient, p_corrected, tier),
                sample_n=len(entries),
                statement=statement,
                flags={
                    **_base_flags(
                        p_value=p_value,
                        p_corrected=p_corrected,
                        method="pointbiserial",
                    ),
                    "weekday_confounded": weekday_confounded,
                    "min_tag_usages": settings.ANALYTICS_MIN_TAG_USAGES,
                },
                payload={
                    "tagged_count": tagged_count,
                    "untagged_count": untagged_count,
                    "tagged_mood_avg": round(tagged_mood, 2),
                    "untagged_mood_avg": round(untagged_mood, 2),
                    "p_corrected": round(p_corrected, 4),
                },
                generated_for_date=generated_for_date,
            )
        )
    return candidates


def _weekday_candidates(
    entries: Sequence[AnalyticsEntry],
    *,
    tier: InsightTier,
    generated_for_date: date_type,
) -> list[InsightCandidate]:
    if len(entries) < MIN_WEEKDAY_ENTRIES:
        return []

    overall_avg = sum(entry.mood_score for entry in entries) / len(entries)
    by_weekday: dict[int, list[int]] = defaultdict(list)
    for entry in entries:
        by_weekday[entry.entry_date.weekday()].append(entry.mood_score)

    weekday_avgs = {
        weekday: sum(values) / len(values)
        for weekday, values in by_weekday.items()
        if len(values) >= 1
    }
    if not weekday_avgs:
        return []

    weekday, avg = max(weekday_avgs.items(), key=lambda item: abs(item[1] - overall_avg))
    delta = avg - overall_avg
    if abs(delta) < MIN_WEEKDAY_DELTA:
        return []

    direction = _direction(delta, "higher", "lower")
    label = _WEEKDAY_LABELS[weekday]
    statement = (
        f"{label}s currently line up with {direction} mood than your overall average. "
        "This is an early calendar pattern, not a diagnosis."
    )
    effect_size = round(delta, 4)
    return [
        InsightCandidate(
            insight_type=InsightType.WEEKDAY_PATTERN,
            tier=tier,
            metric="mood_score",
            subject_type="weekday",
            subject_id=None,
            subject_label=label,
            effect_size=effect_size,
            confidence=_confidence(effect_size, None, tier),
            sample_n=len(entries),
            statement=statement,
            flags={
                **_base_flags(p_value=None, method="weekday_delta"),
                "early_pattern": len(entries) < DEVELOPING_ENTRY_COUNT,
            },
            payload={
                "weekday": weekday,
                "weekday_mood_avg": round(avg, 2),
                "weekday_mood_avgs": {
                    str(day): round(sum(values) / len(values), 2)
                    for day, values in sorted(by_weekday.items())
                },
                "weekday_entry_counts": {
                    str(day): len(values) for day, values in sorted(by_weekday.items())
                },
                "overall_mood_avg": round(overall_avg, 2),
                "weekday_entry_count": len(by_weekday[weekday]),
            },
            generated_for_date=generated_for_date,
        )
    ]


def generate_insight_candidates(
    entries: Sequence[AnalyticsEntry],
    tags: Iterable[TagSnapshot] = (),
    *,
    as_of: date_type | None = None,
) -> list[InsightCandidate]:
    """Generate deterministic insight candidates from user-owned data."""

    daily_entries = _dedupe_daily_entries(entries)
    if not daily_entries:
        return []

    generated_for_date = as_of or daily_entries[-1].entry_date
    tier = confidence_tier_for_sample(len(daily_entries))
    if tier is InsightTier.NONE:
        return []

    tags_by_id = {tag.id: tag for tag in tags}
    candidates = [
        *_weekday_candidates(daily_entries, tier=tier, generated_for_date=generated_for_date),
        *_spearman_candidates(daily_entries, tier=tier, generated_for_date=generated_for_date),
        *_pointbiserial_candidates(
            daily_entries,
            tags_by_id,
            tier=tier,
            generated_for_date=generated_for_date,
        ),
    ]
    return sorted(
        candidates,
        key=lambda candidate: (
            -(candidate.confidence or 0),
            -abs(candidate.effect_size or 0),
            candidate.insight_type.value,
            candidate.metric,
            candidate.subject_label or "",
        ),
    )


async def _load_analytics_inputs(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    as_of: date_type,
) -> tuple[list[AnalyticsEntry], list[TagSnapshot]]:
    result = await db.execute(
        select(Entry)
        # Temporal integrity guard: analytics must follow entry_date only.
        # created_at/updated_at would leak look-ahead bias for backdated entries.
        .where(Entry.user_id == user_id, Entry.entry_date < as_of)
        .order_by(Entry.entry_date.asc(), Entry.slot.asc())
    )
    entries = list(result.scalars().all())
    if not entries:
        return [], []

    tag_rows = await db.execute(
        select(EntryTag.entry_id, Tag)
        .join(Tag, Tag.id == EntryTag.tag_id)
        .join(Entry, Entry.id == EntryTag.entry_id)
        .where(EntryTag.user_id == user_id, Entry.user_id == user_id, Entry.entry_date < as_of)
    )
    tag_ids_by_entry: dict[uuid.UUID, set[uuid.UUID]] = defaultdict(set)
    tags_by_id: dict[uuid.UUID, TagSnapshot] = {}
    for entry_id, tag in tag_rows.all():
        tag_ids_by_entry[entry_id].add(tag.id)
        tags_by_id[tag.id] = TagSnapshot(id=tag.id, label=tag.name, slug=tag.slug)

    return [
        AnalyticsEntry(
            id=entry.id,
            entry_date=entry.entry_date,
            mood_score=entry.mood_score,
            energy=entry.energy,
            stress=entry.stress,
            tag_ids=frozenset(tag_ids_by_entry.get(entry.id, set())),
        )
        for entry in entries
    ], list(tags_by_id.values())


async def generate_and_store_insights(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    as_of: date_type | None = None,
) -> list[Insight]:
    """Regenerate and store M3 insight rows for a user/date.

    The function is idempotent for ``(user_id, generated_for_date)`` by deleting
    existing rows for that date before inserting the new candidates. The caller
    must bind the user's DEK before flushing because ``Insight.statement_enc``
    uses :class:`app.core.crypto.EncryptedString`.
    """

    generated_for_date = as_of or datetime.now(UTC).date()
    entries, tags = await _load_analytics_inputs(db, user_id=user_id, as_of=generated_for_date)
    candidates = generate_insight_candidates(entries, tags, as_of=generated_for_date)

    await db.execute(
        delete(Insight).where(
            Insight.user_id == user_id,
            Insight.generated_for_date == generated_for_date,
        )
    )

    insights = [
        Insight(
            user_id=user_id,
            insight_type=candidate.insight_type,
            tier=candidate.tier,
            metric=candidate.metric,
            subject_type=candidate.subject_type,
            subject_id=candidate.subject_id,
            subject_label=candidate.subject_label,
            effect_size=candidate.effect_size,
            confidence=candidate.confidence,
            sample_n=candidate.sample_n,
            statement_enc=candidate.statement,
            flags=candidate.flags,
            payload=candidate.payload,
            generated_for_date=candidate.generated_for_date,
        )
        for candidate in candidates
    ]
    for insight in insights:
        db.add(insight)
    await db.flush()
    logger.info(
        "insights.generated",
        extra={"user_id": str(user_id), "insight_count": len(insights)},
    )
    return insights
