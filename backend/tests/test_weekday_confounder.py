"""Tests for OLS weekday confounder checks (#146)."""

from __future__ import annotations

from datetime import date, timedelta

from app.services.symptom_analytics import DailySymptomEntry, compute_symptom_metric_associations
from app.services.symptom_analytics import SymptomRef as AnalyticsSymptomRef
from app.services.weekday_confounder import (
    is_metric_association_weekday_confounded,
    is_pair_cooccurrence_weekday_confounded,
)


def _daily(
    day: date,
    *,
    mood: int = 3,
    symptom: bool = False,
    tag: bool = False,
    symptom_id=None,
    tag_id=None,
) -> DailySymptomEntry:
    import uuid

    symptom_uuid = symptom_id or uuid.uuid4()
    tag_uuid = tag_id or uuid.uuid4()
    return DailySymptomEntry(
        entry_date=day,
        mood_score=mood,
        energy=3,
        stress=3,
        tag_ids=frozenset({tag_uuid}) if tag else frozenset(),
        symptom_ids=frozenset({symptom_uuid}) if symptom else frozenset(),
    )


def test_metric_association_confounded_when_weekday_explains_mood() -> None:
    start = date(2026, 1, 5)  # Monday
    entries = []
    for offset in range(28):
        day = start + timedelta(days=offset)
        is_monday = day.weekday() == 0
        entries.append(
            _daily(
                day,
                mood=2 if is_monday else 4,
                symptom=is_monday,
            )
        )

    symptom_id = next(iter(entries[0].symptom_ids))
    metric_values = [entry.mood_score for entry in entries]
    binary = [1 if symptom_id in entry.symptom_ids else 0 for entry in entries]

    assert is_metric_association_weekday_confounded(
        [entry.entry_date for entry in entries],
        metric_values,
        binary,
        raw_coefficient=-0.8,
        raw_p_value=0.001,
    )


def test_metric_association_not_confounded_when_signal_survives_weekday_adjustment() -> None:
    import uuid

    symptom_id = uuid.uuid4()
    start = date(2026, 1, 1)
    entries = [
        DailySymptomEntry(
            entry_date=start + timedelta(days=offset),
            mood_score=2 if offset % 2 == 0 else 5,
            energy=3,
            stress=3,
            tag_ids=frozenset(),
            symptom_ids=frozenset({symptom_id}) if offset % 2 == 0 else frozenset(),
        )
        for offset in range(30)
    ]
    metric_values = [entry.mood_score for entry in entries]
    binary = [1 if symptom_id in entry.symptom_ids else 0 for entry in entries]

    assert not is_metric_association_weekday_confounded(
        [entry.entry_date for entry in entries],
        metric_values,
        binary,
        raw_coefficient=-0.9,
        raw_p_value=0.001,
    )


def test_pair_cooccurrence_confounded_when_weekday_explains_overlap() -> None:
    import uuid

    symptom_id = uuid.uuid4()
    tag_id = uuid.uuid4()
    start = date(2026, 1, 4)  # Sunday
    entries = [
        DailySymptomEntry(
            entry_date=start + timedelta(days=offset),
            mood_score=3,
            energy=3,
            stress=3,
            tag_ids=frozenset({tag_id}) if offset % 7 == 0 else frozenset(),
            symptom_ids=frozenset({symptom_id}) if offset % 7 == 0 else frozenset(),
        )
        for offset in range(28)
    ]

    assert is_pair_cooccurrence_weekday_confounded(
        [entry.entry_date for entry in entries],
        [1 if symptom_id in entry.symptom_ids else 0 for entry in entries],
        [1 if tag_id in entry.tag_ids else 0 for entry in entries],
    )


def test_symptom_metric_candidates_mark_weekday_confounded() -> None:
    import uuid

    symptom_id = uuid.uuid4()
    symptom = AnalyticsSymptomRef(id=symptom_id, label="Headache", slug="headache")
    start = date(2026, 1, 5)
    entries = [
        DailySymptomEntry(
            entry_date=start + timedelta(days=offset),
            mood_score=2 if (start + timedelta(days=offset)).weekday() == 0 else 4,
            energy=3,
            stress=3,
            tag_ids=frozenset(),
            symptom_ids=frozenset({symptom_id})
            if (start + timedelta(days=offset)).weekday() == 0
            else frozenset(),
        )
        for offset in range(30)
    ]

    findings = compute_symptom_metric_associations(entries, {symptom_id: symptom})
    assert findings
    assert any(finding.weekday_confounded for finding in findings)
