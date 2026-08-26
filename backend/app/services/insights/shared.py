"""Shared types, constants and helpers for the insight engine families.

Split out of the former monolithic ``insight_engine`` module (#777). Holds the
plain data structures crossing the analytics thread boundary, the M3 tier
constants, and the small pure helpers reused by every insight family. No
SQLAlchemy session or ORM object appears here — see
:mod:`app.services.insight_engine` for the DB loaders and orchestration.
"""

from __future__ import annotations

import math
import uuid
from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import date as date_type
from typing import Any, Literal

from scipy.stats import chisquare
from statsmodels.stats.multitest import multipletests

from app.core.config import settings
from app.models.entry import WorkContext
from app.models.insight import InsightTier, InsightType

EARLY_ENTRY_COUNT = 3
PRELIMINARY_ENTRY_COUNT = 8
DEVELOPING_ENTRY_COUNT = 15
ROBUST_ENTRY_COUNT = 30
MIN_WEEKDAY_ENTRIES = 7
MIN_BIVARIATE_ENTRIES = DEVELOPING_ENTRY_COUNT
MIN_TAG_GROUP_SIZE = 2
MIN_ABS_EFFECT_SIZE = 0.25
MIN_WEEKDAY_DELTA = 0.5
MIN_CONTEXT_GROUP_SIZE = 2
MIN_CONTEXT_DELTA = 0.5
FDR_ALPHA = 0.05

MetricName = Literal["mood_score", "energy", "stress"]

_METRIC_LABELS: dict[MetricName, str] = {
    "mood_score": "mood",
    "energy": "energy",
    "stress": "stress",
}
# M8 Sprint 2 (#172): manual sleep metrics correlated against mood.
SleepMetricName = Literal["sleep_minutes", "sleep_quality"]
_SLEEP_METRIC_LABELS: dict[SleepMetricName, str] = {
    "sleep_minutes": "sleep duration",
    "sleep_quality": "sleep quality",
}
# A sleep↔mood correlation needs at least this many days that actually recorded
# sleep (pairwise deletion), matching the bivariate bar for other correlations.
MIN_SLEEP_OBSERVATIONS = MIN_BIVARIATE_ENTRIES
_WEEKDAY_LABELS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
_WORK_CONTEXT_LABELS: dict[WorkContext, str] = {
    WorkContext.HOMEOFFICE: "Home office",
    WorkContext.OFFICE: "Office",
    WorkContext.TRAVEL: "Travel",
    WorkContext.VACATION: "Vacation",
    WorkContext.SICK: "Sick leave",
    WorkContext.WEEKEND: "Weekend",
}


@dataclass(frozen=True)
class AnalyticsEntry:
    """Daily row used by the insight engine."""

    id: uuid.UUID
    entry_date: date_type
    mood_score: int
    energy: int
    stress: int
    work_context: WorkContext = WorkContext.HOMEOFFICE
    tag_ids: frozenset[uuid.UUID] = field(default_factory=frozenset)
    symptom_ids: frozenset[uuid.UUID] = field(default_factory=frozenset)
    # M8 Sprint 2 (#172): optional manual sleep metrics. None when the day has no
    # sleep record — sleep↔mood correlations use pairwise deletion on these.
    sleep_minutes: int | None = None
    sleep_quality: int | None = None


@dataclass(frozen=True)
class TagSnapshot:
    """Tag metadata needed for statement rendering."""

    id: uuid.UUID
    label: str
    slug: str
    is_default: bool = False


@dataclass(frozen=True)
class SymptomSnapshot:
    """Symptom metadata needed for M7 multivariate analytics."""

    id: uuid.UUID
    label: str
    slug: str
    is_default: bool = False


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


def _optional_mean_round(values: Sequence[int | None]) -> int | None:
    """Mean of the present values, rounded; None when every value is missing.

    Used to collapse multi-slot sleep records into one daily value while
    preserving "no sleep recorded" as None (M8 Sprint 2).
    """
    present = [value for value in values if value is not None]
    if not present:
        return None
    return round(sum(present) / len(present))


def display_metric_value(
    metric: MetricName, raw: int, *, scale_min: int = 1, scale_max: int = 5
) -> int:
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


def _mean(values: Sequence[int]) -> float:
    return sum(values) / len(values)


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


def is_work_context_biased(
    entries: Sequence[AnalyticsEntry],
    tag_id: uuid.UUID,
    *,
    min_count: int = MIN_TAG_GROUP_SIZE,
    threshold_p: float = FDR_ALPHA,
) -> bool:
    """Return True when a tag is concentrated in specific work contexts."""

    if len(entries) < ROBUST_ENTRY_COUNT:
        return False

    contexts = sorted({entry.work_context for entry in entries}, key=lambda item: item.value)
    if len(contexts) < 2:
        return False

    observed = [
        sum(1 for entry in entries if tag_id in entry.tag_ids and entry.work_context == context)
        for context in contexts
    ]
    total = sum(observed)
    if total < min_count:
        return False

    context_counts = [
        sum(1 for entry in entries if entry.work_context == context) for context in contexts
    ]
    expected = [total * context_count / len(entries) for context_count in context_counts]
    result = chisquare(observed, f_exp=expected)
    p_value = _finite_float(result.pvalue)
    return p_value is not None and p_value < threshold_p


def _confounders(
    *,
    weekday_confounded: bool,
    work_context_confounded: bool,
    calendar_context_confounded: bool,
) -> list[str]:
    values: list[str] = []
    if weekday_confounded:
        values.append("weekday")
    if work_context_confounded:
        values.append("work_context")
    if calendar_context_confounded and not values:
        values.append("calendar_context")
    return values


def _primary_confounder(confounders: Sequence[str]) -> str | None:
    return confounders[0] if confounders else None


def _context_confounded_statement(
    statement: str,
    *,
    weekday_confounded: bool,
    work_context_confounded: bool,
    calendar_context_confounded: bool,
) -> str:
    if not calendar_context_confounded:
        return statement
    if work_context_confounded:
        return f"{statement} Note: this pattern occurs primarily in specific work contexts."
    if weekday_confounded:
        return f"{statement} Note: this pattern occurs primarily on specific weekdays."
    return f"{statement} Note: this pattern may be explained by calendar or work-context patterns."


def _weekday_confounded_statement(statement: str, *, weekday_confounded: bool) -> str:
    return _context_confounded_statement(
        statement,
        weekday_confounded=weekday_confounded,
        work_context_confounded=False,
        calendar_context_confounded=weekday_confounded,
    )


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
                work_context=first.work_context,
                tag_ids=frozenset(tag_id for row in rows for tag_id in row.tag_ids),
                symptom_ids=frozenset(symptom_id for row in rows for symptom_id in row.symptom_ids),
                sleep_minutes=_optional_mean_round([row.sleep_minutes for row in rows]),
                sleep_quality=_optional_mean_round([row.sleep_quality for row in rows]),
            )
        )
    return daily


def _canonicalize_tag_aliases(
    entries: Sequence[AnalyticsEntry],
    tags: Iterable[TagSnapshot],
) -> tuple[list[AnalyticsEntry], list[TagSnapshot]]:
    """Collapse default/override tag rows that share the same slug.

    Copy-on-write tag overrides keep the default slug but receive their own
    database ID. Historical entries can therefore reference the curated default
    while newer entries reference the override. Analytics treats both IDs as
    one semantic tag so matrices and insight feeds do not show duplicates such
    as two separate "Alcohol" rows.
    """

    by_slug: dict[str, list[TagSnapshot]] = defaultdict(list)
    for tag in tags:
        by_slug[tag.slug].append(tag)

    canonical_by_slug: dict[str, TagSnapshot] = {}
    aliases: dict[uuid.UUID, uuid.UUID] = {}
    for slug, snapshots in by_slug.items():
        canonical = sorted(
            snapshots,
            key=lambda item: (item.is_default, item.label.casefold(), str(item.id)),
        )[0]
        canonical_by_slug[slug] = canonical
        for snapshot in snapshots:
            aliases[snapshot.id] = canonical.id

    canonical_entries = [
        AnalyticsEntry(
            id=entry.id,
            entry_date=entry.entry_date,
            mood_score=entry.mood_score,
            energy=entry.energy,
            stress=entry.stress,
            work_context=entry.work_context,
            tag_ids=frozenset(aliases.get(tag_id, tag_id) for tag_id in entry.tag_ids),
            symptom_ids=entry.symptom_ids,
            sleep_minutes=entry.sleep_minutes,
            sleep_quality=entry.sleep_quality,
        )
        for entry in entries
    ]
    return canonical_entries, sorted(canonical_by_slug.values(), key=lambda tag: tag.slug)
