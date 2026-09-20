"""Unit tests for Phase 8 write-time covariates and Belastung composite."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta

from app.models.entry import InferredPeriod, WorkContext
from app.models.insight import InsightTier, InsightType
from app.services.entry_write_time import derive_write_time_covariates, inferred_period_for_hour
from app.services.insights.belastung import _belastung_candidates
from app.services.insights.shared import AnalyticsEntry, SymptomSnapshot


def test_inferred_period_buckets() -> None:
    assert inferred_period_for_hour(6) is InferredPeriod.MORNING
    assert inferred_period_for_hour(14) is InferredPeriod.DAYTIME
    assert inferred_period_for_hour(19) is InferredPeriod.EVENING
    assert inferred_period_for_hour(23) is InferredPeriod.AFTER_HOURS
    assert inferred_period_for_hour(2) is InferredPeriod.AFTER_HOURS


def test_derive_write_time_covariates_uses_client_zone() -> None:
    # 21:30 UTC → 22:30 in Europe/Berlin (CEST) → after_hours
    written = datetime(2026, 6, 15, 21, 30, tzinfo=UTC)
    hour, period = derive_write_time_covariates(
        written_at=written,
        client_timezone="Europe/Berlin",
    )
    assert hour == 23
    assert period is InferredPeriod.AFTER_HOURS


def _entry(
    day: date,
    *,
    stress: int,
    energy: int,
    work_context: WorkContext = WorkContext.OFFICE,
    symptom_ids: frozenset[uuid.UUID] | None = None,
    inferred_period: InferredPeriod | None = None,
) -> AnalyticsEntry:
    return AnalyticsEntry(
        id=uuid.uuid4(),
        entry_date=day,
        mood_score=3,
        energy=energy,
        stress=stress,
        work_context=work_context,
        symptom_ids=symptom_ids or frozenset(),
        inferred_period=inferred_period,
    )


def test_belastung_candidates_require_opt_in_and_pattern() -> None:
    fatigue_id = uuid.uuid4()
    fatigue = SymptomSnapshot(id=fatigue_id, label="Fatigue", slug="fatigue", is_default=True)
    as_of = date(2026, 6, 30)
    recent = [
        _entry(
            as_of - timedelta(days=offset),
            stress=5,
            energy=1,
            symptom_ids=frozenset({fatigue_id}),
            work_context=WorkContext.OFFICE,
            inferred_period=InferredPeriod.AFTER_HOURS,
        )
        for offset in range(14)
    ]
    prior = [
        _entry(
            as_of - timedelta(days=14 + offset),
            stress=2,
            energy=4,
            work_context=WorkContext.WEEKEND if offset % 2 == 0 else WorkContext.OTHER,
        )
        for offset in range(14)
    ]
    entries = [*prior, *recent]

    assert (
        _belastung_candidates(
            entries,
            [],
            [fatigue],
            tier=InsightTier.ROBUST,
            generated_for_date=as_of,
            enabled=False,
        )
        == []
    )

    candidates = _belastung_candidates(
        entries,
        [],
        [fatigue],
        tier=InsightTier.ROBUST,
        generated_for_date=as_of,
        enabled=True,
    )
    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.insight_type is InsightType.BELASTUNG_PATTERN
    assert candidate.flags.get("heuristic") is True
    assert candidate.payload["fatigue_days_recent"] == 14
    assert candidate.payload["recovery_days_prior"] >= 1
    assert (
        "heuristic" in candidate.statement.lower() or "not a medical" in candidate.statement.lower()
    )


def test_write_time_covariates_survive_daily_normalization() -> None:
    """#875 / #892: both normalization helpers must carry the write-time fields.

    Candidate generation always runs entries through `_dedupe_daily_entries` and
    `_canonicalize_tag_aliases`. Both rebuilt `AnalyticsEntry` without copying
    `logged_local_hour` / `inferred_period`, so `inferred_period` was always None
    by the time `_belastung_candidates` read it and `after_hours_days_recent` was
    permanently zero — the after-hours signal could never fire in production.
    """
    from app.services.insights.shared import (
        _canonicalize_tag_aliases,
        _dedupe_daily_entries,
    )

    day = date(2026, 3, 2)
    entries = [
        AnalyticsEntry(
            id=uuid.uuid4(),
            entry_date=day,
            mood_score=3,
            energy=3,
            stress=3,
            work_context=WorkContext.OFFICE,
            tag_ids=frozenset(),
            symptom_ids=frozenset(),
            logged_local_hour=23,
            inferred_period=InferredPeriod.AFTER_HOURS,
        )
    ]

    deduped = _dedupe_daily_entries(entries)
    assert deduped[0].inferred_period is InferredPeriod.AFTER_HOURS
    assert deduped[0].logged_local_hour == 23

    canonical, _ = _canonicalize_tag_aliases(deduped, [])
    assert canonical[0].inferred_period is InferredPeriod.AFTER_HOURS
    assert canonical[0].logged_local_hour == 23


def test_belastung_needs_a_populated_prior_window() -> None:
    """#956: no comparison window means no comparative claim.

    Every predicate is comparative and the statement says "than in the two weeks
    before". The `is None` escapes made all three fire when the prior window was
    empty, so a user with a week of entries and nothing before them was told
    their load had risen against a window that did not exist — while the payload
    reported `prior_n: 0`.
    """
    as_of = date(2026, 3, 20)
    # Seven consecutive days ending at as_of, and nothing before them.
    entries = [
        AnalyticsEntry(
            id=uuid.uuid4(),
            entry_date=as_of - timedelta(days=offset),
            mood_score=2,
            energy=2,
            stress=5,
            work_context=WorkContext.OFFICE,
            tag_ids=frozenset(),
            symptom_ids=frozenset(),
        )
        for offset in range(7)
    ]

    assert (
        _belastung_candidates(
            entries,
            tags=[],
            symptoms=[],
            tier=InsightTier.ROBUST,
            generated_for_date=as_of,
            enabled=True,
        )
        == []
    )
