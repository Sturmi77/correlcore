"""Health Data Maturity service (Issue #852).

Computes the honest "Datenreife" / data-readiness panel for Trends: a coarse
analysis-maturity phase plus neutral coverage ratios (entry / sleep / symptom)
over a rolling window, with per-section progressive-disclosure gates.

This is deliberately a *coverage/maturity* overview, never a physiological or
medical readiness score (spec Non-Goals). It only ever emits counts and ratios
— never plaintext symptom names or concrete sleep values — so it is safe to log
and free of Art. 9 leaks (spec §8).

Lives in its own module (not ``stats_service``) because it depends on
``insight_service.get_insight_maturity`` and ``insight_service`` already imports
``stats_service`` — importing back the other way would be circular.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from datetime import date as date_type

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.consent_log import CONSENT_TYPE_HEALTH_CONNECT
from app.models.entry import Entry
from app.models.symptom import EntrySymptom, Symptom
from app.schemas.stats import (
    CoverageMetric,
    HealthConnectStatus,
    HealthContextCoverage,
    HealthContextMaturity,
    HealthContextResponse,
    HealthContextSection,
)
from app.services.consent_service import is_consent_granted
from app.services.insight_service import get_insight_maturity
from app.services.multivariate_analytics import (
    MIN_SLEEP_COLUMN_COVERAGE,
    MIN_SLEEP_COLUMN_OBSERVATIONS,
)
from app.services.symptom_analytics import MIN_SYMPTOM_ANALYTICS_ENTRIES

#: Rolling coverage window in days (spec D4 — matches the tag-cluster window and
#: makes long histories, e.g. a 122-day streak, irrelevant to the ratios).
HEALTH_CONTEXT_WINDOW_DAYS = 90


def _today() -> date_type:
    return datetime.now(UTC).date()


def _pct(days_with_data: int, window_days: int) -> float:
    if window_days <= 0:
        return 0.0
    return round(days_with_data / window_days, 2)


async def _count_distinct_entry_days(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    start: date_type,
    as_of: date_type,
) -> int:
    """Distinct days with at least one entry in the window."""

    result = await db.execute(
        select(func.count(func.distinct(Entry.entry_date))).where(
            Entry.user_id == user_id,
            Entry.entry_date >= start,
            Entry.entry_date <= as_of,
        )
    )
    return int(result.scalar_one() or 0)


async def _count_distinct_sleep_days(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    start: date_type,
    as_of: date_type,
) -> int:
    """Distinct days with a sleep signal in the window.

    Canonical sleep signal is ``sleep_minutes`` (the duration column the insight
    engine's multivariate sleep gate governs via ``MIN_SLEEP_COLUMN_COVERAGE``),
    so the coverage number lines up with what actually unlocks sleep insights.
    """

    result = await db.execute(
        select(func.count(func.distinct(Entry.entry_date))).where(
            Entry.user_id == user_id,
            Entry.entry_date >= start,
            Entry.entry_date <= as_of,
            Entry.sleep_minutes.is_not(None),
        )
    )
    return int(result.scalar_one() or 0)


async def _count_distinct_symptom_days(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    start: date_type,
    as_of: date_type,
) -> int:
    """Distinct days with at least one logged symptom (intensity > 0)."""

    result = await db.execute(
        select(func.count(func.distinct(Entry.entry_date)))
        .select_from(EntrySymptom)
        .join(Entry, Entry.id == EntrySymptom.entry_id)
        .join(Symptom, Symptom.id == EntrySymptom.symptom_id)
        .where(
            EntrySymptom.user_id == user_id,
            EntrySymptom.intensity > 0,
            Entry.user_id == user_id,
            Entry.entry_date >= start,
            Entry.entry_date <= as_of,
            (Symptom.is_default.is_(True)) | (Symptom.user_id == user_id),
        )
    )
    return int(result.scalar_one() or 0)


def _symptom_section(current_entries: int) -> HealthContextSection:
    """Gate: symptom analytics unlock at MIN_SYMPTOM_ANALYTICS_ENTRIES entries."""

    if current_entries >= MIN_SYMPTOM_ANALYTICS_ENTRIES:
        return HealthContextSection(
            id="symptom",
            unlocked=True,
            reason="ok",
            entries_until_unlock=None,
            copy_key="trends.maturity.symptom.ok",
        )
    return HealthContextSection(
        id="symptom",
        unlocked=False,
        reason="insufficient_entries",
        entries_until_unlock=MIN_SYMPTOM_ANALYTICS_ENTRIES - current_entries,
        copy_key="trends.maturity.symptom.insufficient_entries",
    )


def _sleep_section(sleep_days: int, sleep_pct: float) -> HealthContextSection:
    """Gate: sleep insights unlock at coverage >= 0.5 AND >= 15 observations."""

    if sleep_pct >= MIN_SLEEP_COLUMN_COVERAGE and sleep_days >= MIN_SLEEP_COLUMN_OBSERVATIONS:
        return HealthContextSection(
            id="sleep",
            unlocked=True,
            reason="ok",
            entries_until_unlock=None,
            copy_key="trends.maturity.sleep.ok",
        )
    return HealthContextSection(
        id="sleep",
        unlocked=False,
        reason="insufficient_coverage",
        entries_until_unlock=None,
        copy_key="trends.maturity.sleep.insufficient_coverage",
    )


async def get_health_context(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    as_of: date_type | None = None,
) -> HealthContextResponse:
    """Build the Health Data Maturity DTO for the Trends panel (spec §6)."""

    as_of = as_of or _today()
    window = HEALTH_CONTEXT_WINDOW_DAYS
    start = as_of - timedelta(days=window - 1)

    maturity = await get_insight_maturity(db, user_id=user_id)

    entry_days = await _count_distinct_entry_days(db, user_id=user_id, start=start, as_of=as_of)
    sleep_days = await _count_distinct_sleep_days(db, user_id=user_id, start=start, as_of=as_of)
    symptom_days = await _count_distinct_symptom_days(db, user_id=user_id, start=start, as_of=as_of)

    sleep_pct = _pct(sleep_days, window)

    coverage = HealthContextCoverage(
        entry=CoverageMetric(
            days_with_data=entry_days, window_days=window, pct=_pct(entry_days, window)
        ),
        sleep=CoverageMetric(days_with_data=sleep_days, window_days=window, pct=sleep_pct),
        symptom=CoverageMetric(
            days_with_data=symptom_days, window_days=window, pct=_pct(symptom_days, window)
        ),
    )

    sections = [
        _symptom_section(maturity.current_entries),
        _sleep_section(sleep_days, sleep_pct),
    ]

    # Health-Connect meta is optional and consent-gated. v1 exposes only the
    # consent flag (no last_sync/import state source yet) and never any imported
    # health value. Without consent the whole object is null (spec D6/§8).
    consent = await is_consent_granted(
        db, user_id=user_id, consent_type=CONSENT_TYPE_HEALTH_CONNECT
    )
    health_connect = (
        HealthConnectStatus(consent=True, last_sync_at=None, sleep_import_ok=None)
        if consent
        else None
    )

    return HealthContextResponse(
        as_of=as_of,
        coverage_window_days=window,
        maturity=HealthContextMaturity(
            phase=maturity.phase.value,
            phase_index=maturity.phase_index,
            current_entries=maturity.current_entries,
            next_phase_at=maturity.next_phase_at,
            entries_until_next=maturity.entries_until_next,
        ),
        coverage=coverage,
        sections=sections,
        health_connect=health_connect,
    )
