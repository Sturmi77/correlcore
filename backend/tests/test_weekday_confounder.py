"""Tests for OLS weekday confounder checks (#146)."""

from __future__ import annotations

from datetime import date, timedelta

from app.models.entry import WorkContext
from app.services.symptom_analytics import (
    DailySymptomEntry,
    compute_symptom_metric_associations,
    is_work_context_biased_signal,
)
from app.services.symptom_analytics import SymptomRef as AnalyticsSymptomRef
from app.services.weekday_confounder import (
    MetricAdjustmentResult,
    SameSituationFrequencies,
    evaluate_metric_association_weekday,
    is_metric_association_calendar_context_confounded,
    is_metric_association_weekday_confounded,
    is_pair_cooccurrence_calendar_context_confounded,
    is_pair_cooccurrence_weekday_confounded,
    same_work_context_metric_frequencies,
    situation_adjustment_payload,
)


def _daily(
    day: date,
    *,
    mood: int = 3,
    symptom: bool = False,
    tag: bool = False,
    symptom_id=None,
    tag_id=None,
    work_context: WorkContext = WorkContext.HOMEOFFICE,
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
        work_context=work_context,
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


def test_metric_association_confounded_when_work_context_explains_mood() -> None:
    import uuid

    symptom_id = uuid.uuid4()
    start = date(2026, 1, 1)
    entries = [
        DailySymptomEntry(
            entry_date=start + timedelta(days=offset),
            mood_score=2 if offset < 10 else 4,
            energy=3,
            stress=3,
            tag_ids=frozenset(),
            symptom_ids=frozenset({symptom_id}) if offset < 10 else frozenset(),
            work_context=WorkContext.OFFICE if offset < 10 else WorkContext.HOMEOFFICE,
        )
        for offset in range(30)
    ]
    metric_values = [entry.mood_score for entry in entries]
    binary = [1 if symptom_id in entry.symptom_ids else 0 for entry in entries]

    assert is_metric_association_calendar_context_confounded(
        [entry.entry_date for entry in entries],
        [entry.work_context.value for entry in entries],
        metric_values,
        binary,
        raw_coefficient=-0.8,
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


def test_pair_cooccurrence_confounded_when_work_context_explains_overlap() -> None:
    import uuid

    symptom_id = uuid.uuid4()
    tag_id = uuid.uuid4()
    start = date(2026, 1, 1)
    entries = [
        DailySymptomEntry(
            entry_date=start + timedelta(days=offset),
            mood_score=3,
            energy=3,
            stress=3,
            tag_ids=frozenset({tag_id}) if offset < 8 else frozenset(),
            symptom_ids=frozenset({symptom_id}) if offset < 8 else frozenset(),
            work_context=WorkContext.OFFICE if offset < 8 else WorkContext.HOMEOFFICE,
        )
        for offset in range(30)
    ]

    assert is_pair_cooccurrence_calendar_context_confounded(
        [entry.entry_date for entry in entries],
        [entry.work_context.value for entry in entries],
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


def test_symptom_metric_candidates_mark_work_context_confounded() -> None:
    import uuid

    symptom_id = uuid.uuid4()
    symptom = AnalyticsSymptomRef(id=symptom_id, label="Headache", slug="headache")
    start = date(2026, 1, 1)
    entries = [
        DailySymptomEntry(
            entry_date=start + timedelta(days=offset),
            mood_score=2 if offset < 10 else 4,
            energy=3,
            stress=3,
            tag_ids=frozenset(),
            symptom_ids=frozenset({symptom_id}) if offset < 10 else frozenset(),
            work_context=WorkContext.OFFICE if offset < 10 else WorkContext.HOMEOFFICE,
        )
        for offset in range(30)
    ]

    findings = compute_symptom_metric_associations(entries, {symptom_id: symptom})

    assert findings
    assert any(finding.work_context_confounded for finding in findings)
    assert any(finding.calendar_context_confounded for finding in findings)


def test_symptom_work_context_bias_uses_available_context_day_baseline() -> None:
    import uuid

    symptom_id = uuid.uuid4()
    tag_id = uuid.uuid4()
    start = date(2026, 1, 1)
    entries = [
        DailySymptomEntry(
            entry_date=start + timedelta(days=offset),
            mood_score=3,
            energy=3,
            stress=3,
            tag_ids=frozenset({tag_id}) if offset < 20 or 25 <= offset < 29 else frozenset(),
            symptom_ids=frozenset({symptom_id})
            if offset < 20 or 25 <= offset < 29
            else frozenset(),
            work_context=WorkContext.OFFICE if offset < 25 else WorkContext.HOMEOFFICE,
        )
        for offset in range(30)
    ]

    assert is_work_context_biased_signal(entries, tag_id, kind="tag") is False
    assert is_work_context_biased_signal(entries, symptom_id, kind="symptom") is False


def test_evaluate_metric_association_weekday_exposes_held_coefficient() -> None:
    import uuid

    symptom_id = uuid.uuid4()
    start = date(2026, 1, 1)
    entries = [
        DailySymptomEntry(
            entry_date=start + timedelta(days=offset),
            mood_score=5 if offset % 2 == 0 else 2,
            energy=3,
            stress=3,
            tag_ids=frozenset(),
            symptom_ids=frozenset({symptom_id}) if offset % 2 == 0 else frozenset(),
            work_context=WorkContext.HOMEOFFICE,
        )
        for offset in range(28)
    ]
    metric_values = [float(entry.mood_score) for entry in entries]
    binary = [1 if symptom_id in entry.symptom_ids else 0 for entry in entries]
    result = evaluate_metric_association_weekday(
        [entry.entry_date for entry in entries],
        metric_values,
        binary,
        raw_coefficient=0.7,
        raw_p_value=0.001,
    )
    assert result.adjusted_coefficient is not None
    assert result.adjusted_p is not None
    assert result.confounded is False


def test_same_work_context_metric_frequencies_uses_modal_signal_context() -> None:
    contexts = ["office"] * 8 + ["homeoffice"] * 4 + ["office"] * 8
    binary = [1] * 8 + [1] * 4 + [0] * 8
    metrics = [5] * 8 + [3] * 4 + [2] * 8
    freqs = same_work_context_metric_frequencies(contexts, binary, metrics, metric="mood_score")
    assert freqs.context == "office"
    assert freqs.with_n == 8
    assert freqs.without_n == 8
    assert freqs.with_good == 8
    assert freqs.without_good == 0


def test_same_work_context_frequencies_read_stress_on_its_own_scale() -> None:
    """#955: `>= 4` on raw stress counted the most stressful days as the good ones.

    The symptom family reaches this helper once per metric target, stress
    included, so the fixed mood threshold reported a symptom that goes with high
    stress as one that goes with good days.
    """
    contexts = ["office"] * 16
    binary = [1] * 8 + [0] * 8
    # Signal days are highly stressed (5); comparison days are calm (1).
    metrics = [5] * 8 + [1] * 8

    stress = same_work_context_metric_frequencies(contexts, binary, metrics, metric="stress")
    assert stress.with_good == 0, "stress 5 is the worst day, never a good one"
    assert stress.without_good == 8

    # Same numbers on a normal scale mean the opposite.
    mood = same_work_context_metric_frequencies(contexts, binary, metrics, metric="mood_score")
    assert mood.with_good == 8
    assert mood.without_good == 0


def test_survives_is_none_when_no_adjustment_ran() -> None:
    """#956: `confounded=False` from an early exit is "could not tell", not "held".

    `evaluate_metric_association_*` returns that shape when the row count is
    below MIN_OLS_ROWS, when there is a single distinct context, and on a
    LinAlgError — cases where no regression ever ran. Reading it as a verdict
    made the signal page assert the association survives an adjustment that
    never happened.
    """
    not_run = MetricAdjustmentResult(False, None, None, 8)

    payload = situation_adjustment_payload(
        weekday=not_run,
        calendar=not_run,
        situation=SameSituationFrequencies(
            context=None, with_n=0, without_n=0, with_good=0, without_good=0
        ),
        primary_confounder=None,
        metric="mood_score",
    )
    assert payload["situation_effect_survives"] is None


def test_survives_is_true_only_with_a_fit_behind_it() -> None:
    fitted = MetricAdjustmentResult(False, 0.31, 0.01, 40)
    not_run = MetricAdjustmentResult(False, None, None, 8)

    held = situation_adjustment_payload(
        weekday=fitted,
        calendar=not_run,
        situation=SameSituationFrequencies(
            context=None, with_n=0, without_n=0, with_good=0, without_good=0
        ),
        primary_confounder="weekday",
        metric="mood_score",
    )
    assert held["situation_effect_survives"] is True

    # Same fit, but the primary confounder points at the arm that never ran.
    undetermined = situation_adjustment_payload(
        weekday=fitted,
        calendar=not_run,
        situation=SameSituationFrequencies(
            context=None, with_n=0, without_n=0, with_good=0, without_good=0
        ),
        primary_confounder="work_context",
        metric="mood_score",
    )
    assert undetermined["situation_effect_survives"] is None


def test_survives_is_false_when_the_adjustment_says_confounded() -> None:
    confounded = MetricAdjustmentResult(True, None, None, 40)
    payload = situation_adjustment_payload(
        weekday=confounded,
        calendar=MetricAdjustmentResult(False, 0.3, 0.02, 40),
        situation=SameSituationFrequencies(
            context=None, with_n=0, without_n=0, with_good=0, without_good=0
        ),
        primary_confounder="weekday",
        metric="mood_score",
    )
    assert payload["situation_effect_survives"] is False
