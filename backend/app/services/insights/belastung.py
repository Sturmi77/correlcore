"""Phase 8 / #875 — Belastungsmuster composite (heuristic, opt-in overlay).

Named composite over the last 14 days vs the prior 14 days:
Stress↑ + Energy↓ + fatigue frequency, plus recovery-day share and an
after-hours write signal when ``inferred_period`` is available.
No new entry fields; no clinical inventories.
"""

from __future__ import annotations

import math
import uuid
from collections.abc import Sequence
from datetime import date as date_type
from datetime import timedelta

from app.models.entry import InferredPeriod, WorkContext
from app.models.insight import InsightTier, InsightType
from app.services.insights.shared import (
    AnalyticsEntry,
    InsightCandidate,
    SymptomSnapshot,
    TagSnapshot,
    _confidence,
)

WINDOW_DAYS = 14
MIN_WINDOW_ENTRIES = 7
HIGH_STRESS = 4
LOW_ENERGY = 2
FATIGUE_SLUG = "fatigue"
WORK_INTENSE_SLUG = "work_intense"
ACHIEVEMENT_SLUG = "achievement"
RECOVERY_CONTEXTS = frozenset(
    {WorkContext.VACATION, WorkContext.WEEKEND, WorkContext.OTHER, WorkContext.SICK}
)


def _mean(values: Sequence[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def _slope(values: Sequence[float]) -> float | None:
    """Simple least-squares slope over equal day steps (1..n)."""

    n = len(values)
    if n < 3:
        return None
    xs = list(range(n))
    x_mean = (n - 1) / 2
    y_mean = sum(values) / n
    denom = sum((x - x_mean) ** 2 for x in xs)
    if denom == 0:
        return None
    numer = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, values, strict=True))
    return numer / denom


def _window(
    entries: Sequence[AnalyticsEntry],
    *,
    end: date_type,
    days: int,
) -> list[AnalyticsEntry]:
    start = end - timedelta(days=days - 1)
    return [entry for entry in entries if start <= entry.entry_date <= end]


def _fatigue_id(symptoms: Sequence[SymptomSnapshot]) -> uuid.UUID | None:
    for symptom in symptoms:
        if symptom.slug == FATIGUE_SLUG:
            return symptom.id
    return None


def _tag_id(tags: Sequence[TagSnapshot], slug: str) -> uuid.UUID | None:
    for tag in tags:
        if tag.slug == slug:
            return tag.id
    return None


def _belastung_candidates(
    entries: Sequence[AnalyticsEntry],
    tags: Sequence[TagSnapshot],
    symptoms: Sequence[SymptomSnapshot],
    *,
    tier: InsightTier,
    generated_for_date: date_type,
    enabled: bool,
) -> list[InsightCandidate]:
    if not enabled or tier is InsightTier.NONE:
        return []
    if len(entries) < MIN_WINDOW_ENTRIES:
        return []

    as_of = generated_for_date
    recent = _window(entries, end=as_of, days=WINDOW_DAYS)
    prior_end = as_of - timedelta(days=WINDOW_DAYS)
    prior = _window(entries, end=prior_end, days=WINDOW_DAYS)
    if len(recent) < MIN_WINDOW_ENTRIES:
        return []

    fatigue_id = _fatigue_id(symptoms)
    work_intense_id = _tag_id(tags, WORK_INTENSE_SLUG)
    achievement_id = _tag_id(tags, ACHIEVEMENT_SLUG)

    def fatigue_count(rows: Sequence[AnalyticsEntry]) -> int:
        if fatigue_id is None:
            return 0
        return sum(1 for row in rows if fatigue_id in row.symptom_ids)

    def recovery_count(rows: Sequence[AnalyticsEntry]) -> int:
        return sum(1 for row in rows if row.work_context in RECOVERY_CONTEXTS)

    def after_hours_count(rows: Sequence[AnalyticsEntry]) -> int:
        return sum(
            1 for row in rows if getattr(row, "inferred_period", None) == InferredPeriod.AFTER_HOURS
        )

    recent_stress = [float(row.stress) for row in recent]
    prior_stress = [float(row.stress) for row in prior]
    recent_energy = [float(row.energy) for row in recent]
    prior_energy = [float(row.energy) for row in prior]

    stress_recent = _mean(recent_stress)
    stress_prior = _mean(prior_stress)
    energy_recent = _mean(recent_energy)
    energy_prior = _mean(prior_energy)
    if stress_recent is None or energy_recent is None:
        return []

    fatigue_recent = fatigue_count(recent)
    fatigue_prior = fatigue_count(prior)
    recovery_recent = recovery_count(recent)
    recovery_prior = recovery_count(prior)
    after_hours_recent = after_hours_count(recent)

    stress_up = stress_prior is None or stress_recent >= (stress_prior + 0.25)
    energy_down = energy_prior is None or energy_recent <= (energy_prior - 0.25)
    fatigue_up = fatigue_recent / max(len(recent), 1) > (
        fatigue_prior / max(len(prior), 1) if prior else 0
    )
    if not (stress_up or energy_down or fatigue_up):
        return []

    stress_slope = _slope(recent_stress)
    energy_slope = _slope(recent_energy)
    effect = 0.0
    if stress_prior is not None:
        effect += stress_recent - stress_prior
    if energy_prior is not None:
        effect += energy_prior - energy_recent
    if prior:
        effect += (fatigue_recent / len(recent)) - (fatigue_prior / len(prior))
    effect = round(effect / 3, 4)

    parts: list[str] = []
    if stress_up:
        parts.append("higher stress")
    if energy_down:
        parts.append("lower energy")
    if fatigue_up and fatigue_id is not None:
        parts.append("more fatigue days")
    joined = ", ".join(parts) if parts else "a denser load pattern"
    statement = (
        f"In the last two weeks, {joined} showed up more often together "
        f"than in the two weeks before. This is a heuristic summary of your "
        f"entries — not a medical assessment."
    )

    work_intense_days = (
        sum(1 for row in recent if work_intense_id in row.tag_ids) if work_intense_id else 0
    )
    achievement_days = (
        sum(1 for row in recent if achievement_id in row.tag_ids) if achievement_id else 0
    )

    confidence = _confidence(max(0.2, abs(effect)), 0.2, tier)
    return [
        InsightCandidate(
            insight_type=InsightType.BELASTUNG_PATTERN,
            tier=tier,
            metric="belastung_composite",
            subject_type="composite",
            subject_id=None,
            subject_label="Belastungsmuster",
            effect_size=effect if math.isfinite(effect) else None,
            confidence=confidence,
            sample_n=len(recent),
            statement=statement,
            flags={
                "method": "belastung_composite",
                "heuristic": True,
                "medical_disclaimer_required": True,
                "causal_claim": False,
                "non_result": False,
            },
            payload={
                "kind": "belastung_pattern",
                "heuristic": True,
                "window_days": WINDOW_DAYS,
                "recent_n": len(recent),
                "prior_n": len(prior),
                "stress_avg_recent": round(stress_recent, 2),
                "stress_avg_prior": round(stress_prior, 2) if stress_prior is not None else None,
                "energy_avg_recent": round(energy_recent, 2),
                "energy_avg_prior": round(energy_prior, 2) if energy_prior is not None else None,
                "stress_slope": round(stress_slope, 4) if stress_slope is not None else None,
                "energy_slope": round(energy_slope, 4) if energy_slope is not None else None,
                "fatigue_days_recent": fatigue_recent,
                "fatigue_days_prior": fatigue_prior,
                "recovery_days_recent": recovery_recent,
                "recovery_days_prior": recovery_prior,
                "after_hours_days_recent": after_hours_recent,
                "work_intense_days_recent": work_intense_days,
                "achievement_days_recent": achievement_days,
                "cta_subjects": [
                    {"kind": "tag", "slug": WORK_INTENSE_SLUG},
                    {"kind": "metric", "slug": "sleep_quality"},
                ],
            },
            generated_for_date=generated_for_date,
        )
    ]
