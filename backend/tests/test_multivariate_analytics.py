from __future__ import annotations

import uuid
from datetime import date, timedelta

from app.services.multivariate_analytics import (
    MIN_ML_ENTRIES,
    FeatureKind,
    FeatureMetadata,
    MultivariateEntry,
    build_design_matrix,
    build_lagged_frame,
    m7_time_series_split,
    run_lag_analysis,
    run_lasso_models,
)


def _entry(
    day: date,
    *,
    mood: int = 3,
    energy: int = 3,
    stress: int = 3,
    tag_ids: frozenset[uuid.UUID] = frozenset(),
    symptom_ids: frozenset[uuid.UUID] = frozenset(),
) -> MultivariateEntry:
    return MultivariateEntry(
        entry_date=day,
        mood_score=mood,
        energy=energy,
        stress=stress,
        tag_ids=tag_ids,
        symptom_ids=symptom_ids,
    )


def _feature(kind: FeatureKind, item_id: uuid.UUID, slug: str) -> FeatureMetadata:
    return FeatureMetadata(
        kind=kind,
        key=f"{kind}:{slug}",
        label=slug.title(),
        slug=slug,
        id=item_id,
    )


def test_time_series_split_never_trains_on_future_rows() -> None:
    splitter = m7_time_series_split()

    for train_index, test_index in splitter.split(list(range(MIN_ML_ENTRIES))):
        assert max(train_index) < min(test_index)


def test_design_matrix_contains_eligible_symptoms_and_drops_sparse_features() -> None:
    common_symptom_id = uuid.uuid4()
    rare_symptom_id = uuid.uuid4()
    start = date(2026, 1, 1)
    entries = [
        _entry(
            start + timedelta(days=offset),
            symptom_ids=frozenset(
                {
                    symptom_id
                    for symptom_id, present in (
                        (common_symptom_id, offset % 3 == 0),
                        (rare_symptom_id, offset == 0),
                    )
                    if present
                }
            ),
        )
        for offset in range(30)
    ]

    frame, feature_meta = build_design_matrix(
        entries,
        symptoms={
            common_symptom_id: _feature("symptom", common_symptom_id, "headache"),
            rare_symptom_id: _feature("symptom", rare_symptom_id, "rare"),
        },
    )

    assert f"symptom_{common_symptom_id.hex}" in frame.columns
    assert f"symptom_{rare_symptom_id.hex}" not in frame.columns
    assert feature_meta[f"symptom_{common_symptom_id.hex}"].kind == "symptom"


def test_lasso_waits_for_90_entries_and_is_reproducible() -> None:
    symptom_id = uuid.uuid4()
    start = date(2026, 1, 1)
    entries = [
        _entry(
            start + timedelta(days=offset),
            mood=2 if offset % 3 == 0 else 5,
            symptom_ids=frozenset({symptom_id}) if offset % 3 == 0 else frozenset(),
        )
        for offset in range(MIN_ML_ENTRIES)
    ]
    symptoms = {symptom_id: _feature("symptom", symptom_id, "headache")}
    short_frame, short_meta = build_design_matrix(entries[:-1], symptoms=symptoms)
    full_frame, full_meta = build_design_matrix(entries, symptoms=symptoms)

    assert run_lasso_models(short_frame, short_meta) == []

    first = run_lasso_models(full_frame, full_meta)
    second = run_lasso_models(full_frame, full_meta)

    assert first == second
    assert first
    assert any(
        coefficient.feature.kind == "symptom"
        for finding in first
        for coefficient in finding.features
    )


def test_lag_frame_drops_shift_warmup_rows_without_false_zero_fill() -> None:
    start = date(2026, 1, 1)
    frame, _ = build_design_matrix(
        [
            _entry(start + timedelta(days=offset), mood=offset % 5 + 1, energy=offset % 4 + 1)
            for offset in range(12)
        ]
    )

    lagged = build_lagged_frame(frame, ["mood_score", "energy"], max_lag_days=7)

    assert len(lagged) == 5
    assert not lagged.isna().any().any()
    assert lagged.index.min().date() == start + timedelta(days=7)


def test_lag_frame_uses_calendar_days_not_previous_logged_row() -> None:
    start = date(2026, 1, 1)
    frame, _ = build_design_matrix(
        [
            _entry(start, mood=1, energy=1),
            _entry(start + timedelta(days=1), mood=2, energy=2),
            _entry(start + timedelta(days=10), mood=5, energy=5),
        ]
    )

    lagged = build_lagged_frame(frame, ["mood_score", "energy"], max_lag_days=1)

    assert list(lagged.index.date) == [start + timedelta(days=1)]
    assert int(lagged.iloc[0]["mood_score_lag1"]) == 1


def test_lag_analysis_treats_symptoms_as_targets() -> None:
    tag_id = uuid.uuid4()
    symptom_id = uuid.uuid4()
    start = date(2026, 1, 1)
    entries = []
    for offset in range(100):
        tag_present = offset % 4 == 0
        symptom_present = offset > 0 and (offset - 1) % 4 == 0
        entries.append(
            _entry(
                start + timedelta(days=offset),
                tag_ids=frozenset({tag_id}) if tag_present else frozenset(),
                symptom_ids=frozenset({symptom_id}) if symptom_present else frozenset(),
            )
        )
    frame, feature_meta = build_design_matrix(
        entries,
        tags={tag_id: _feature("tag", tag_id, "stressful-day")},
        symptoms={symptom_id: _feature("symptom", symptom_id, "headache")},
    )

    findings = run_lag_analysis(frame, feature_meta)

    assert any(
        finding.target.kind == "symptom" and finding.feature.kind == "tag" and finding.lag_days == 1
        for finding in findings
    )
