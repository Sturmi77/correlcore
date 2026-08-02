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
    sleep_minutes: int | None = None,
    sleep_quality: int | None = None,
) -> MultivariateEntry:
    return MultivariateEntry(
        entry_date=day,
        mood_score=mood,
        energy=energy,
        stress=stress,
        tag_ids=tag_ids,
        symptom_ids=symptom_ids,
        sleep_minutes=sleep_minutes,
        sleep_quality=sleep_quality,
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


def test_design_matrix_adds_well_covered_sleep_columns() -> None:
    """M8 Sprint 2 (#172): sleep joins as a metric column."""
    start = date(2026, 1, 1)
    # 30 days: full coverage on sleep_minutes (values vary), no sleep_quality at all.
    entries = [
        _entry(
            start + timedelta(days=offset),
            sleep_minutes=420 if offset % 2 == 0 else 480,
        )
        for offset in range(30)
    ]

    frame, feature_meta = build_design_matrix(entries)

    assert "sleep_minutes" in frame.columns
    assert feature_meta["sleep_minutes"].kind == "metric"
    assert feature_meta["sleep_minutes"].label == "sleep duration"
    assert "sleep_quality" not in frame.columns  # never recorded → no column
    assert not frame["sleep_minutes"].isna().any()


def test_design_matrix_keeps_sleep_gaps_as_nan_for_pairwise_deletion() -> None:
    """M8 Sprint 2 (#172): missing sleep days stay NaN — no design-matrix imputation.

    Lag analysis needs real missingness for pairwise deletion (see
    run_lag_analysis); only run_lasso_models imputes, and only fold-locally.
    """
    start = date(2026, 1, 1)
    # 20 of 30 days recorded sleep_minutes (above the coverage floor, but with gaps).
    entries = [
        _entry(
            start + timedelta(days=offset),
            sleep_minutes=None if offset % 3 == 0 else 420 + offset,
        )
        for offset in range(30)
    ]

    frame, _ = build_design_matrix(entries)

    assert "sleep_minutes" in frame.columns
    assert frame["sleep_minutes"].isna().sum() == 10
    recorded_offsets = [offset for offset in range(30) if offset % 3 != 0]
    assert frame["sleep_minutes"].notna().sum() == len(recorded_offsets)


def test_design_matrix_omits_sparsely_covered_sleep_column() -> None:
    start = date(2026, 1, 1)
    # Only 5 of 30 days recorded sleep_minutes → below the coverage floor.
    entries = [
        _entry(
            start + timedelta(days=offset),
            sleep_minutes=450 if offset < 5 else None,
        )
        for offset in range(30)
    ]

    frame, _ = build_design_matrix(entries)

    assert "sleep_minutes" not in frame.columns


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


def test_lasso_handles_sleep_gaps_via_fold_local_imputation() -> None:
    """M8 Sprint 2 (#172): Lasso tolerates NaN sleep gaps via its own imputer step."""
    start = date(2026, 1, 1)
    entries = [
        _entry(
            start + timedelta(days=offset),
            mood=2 if offset % 3 == 0 else 5,
            sleep_minutes=None if offset % 4 == 0 else 400 + (offset % 5) * 10,
        )
        for offset in range(MIN_ML_ENTRIES)
    ]
    frame, feature_meta = build_design_matrix(entries)

    assert frame["sleep_minutes"].isna().any()
    findings = run_lasso_models(frame, feature_meta)

    assert findings == run_lasso_models(frame, feature_meta)


def test_lag_analysis_sleep_predictor_keeps_gappy_pairwise_pairs() -> None:
    """Sleep lag must pairwise-delete on (target, sleep_lagN), not same-day sleep.

    Requiring contemporaneous sleep in ``build_lagged_frame(...).dropna()`` drops
    every gap day and every day-after-gap, wiping most valid prior-sleep→mood
    pairs. With sleep missing every third day, correct pairwise keeps ~2/3 of
    rows while the old blanket dropna kept only ~1/3 (#172).
    """
    start = date(2026, 1, 1)
    entries = []
    for offset in range(MIN_ML_ENTRIES):
        # ~67% coverage (above the 50% floor) with systematic gaps.
        sleep_minutes = None if offset % 3 == 0 else 350 + (offset % 7) * 15
        if offset == 0 or (offset - 1) % 3 == 0:
            # No usable prior sleep — neutral mood with light variance so the
            # series is not constant if these rows ever leak into a pair.
            mood = 2 + (offset % 2)
        else:
            prior_sleep = 350 + ((offset - 1) % 7) * 15
            mood = max(1, min(5, 1 + (prior_sleep - 350) // 20))
        entries.append(
            _entry(start + timedelta(days=offset), mood=mood, sleep_minutes=sleep_minutes)
        )

    frame, feature_meta = build_design_matrix(entries)
    assert "sleep_minutes" in frame.columns
    assert frame["sleep_minutes"].isna().any()

    # Old path: blanket dropna on [mood, sleep, sleep_lag1] keeps only days that
    # have same-day sleep AND prior sleep (~1/3). New path must keep ~2/3.
    broken = build_lagged_frame(
        frame[["mood_score", "sleep_minutes"]],
        ["sleep_minutes"],
        max_lag_days=1,
        dropna=True,
    )
    fixed = build_lagged_frame(
        frame[["mood_score", "sleep_minutes"]],
        ["sleep_minutes"],
        max_lag_days=1,
        dropna=False,
    )
    broken_n = len(broken[["mood_score", "sleep_minutes_lag1"]].dropna()) if len(broken) else 0
    fixed_n = len(fixed[["mood_score", "sleep_minutes_lag1"]].dropna())
    assert fixed_n > broken_n
    assert fixed_n >= (MIN_ML_ENTRIES * 2) // 3 - 1  # warm-up may drop the first day

    findings = run_lag_analysis(
        frame,
        feature_meta,
        max_lag_days=1,
        min_observations=10,
        min_abs_correlation=0.1,
    )
    sleep_to_mood = [
        finding
        for finding in findings
        if finding.feature.key == "sleep_minutes" and finding.target.key == "mood_score"
    ]
    assert sleep_to_mood, "gappy sleep must still produce sleep→mood lag findings"
    assert sleep_to_mood[0].lag_days == 1
    assert sleep_to_mood[0].sample_n == fixed_n


def test_lag_analysis_never_targets_sleep_and_uses_pairwise_deletion() -> None:
    """M8 Sprint 2 (#172): sleep is a lag predictor only, and its own missing days
    don't shrink unrelated tag/symptom lag pairs (real pairwise deletion)."""
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
                # Sparse, gap-ridden sleep coverage on top of the tag/symptom signal.
                sleep_minutes=None if offset % 3 == 0 else 400 + (offset % 6) * 10,
            )
        )
    frame_with_sleep, meta_with_sleep = build_design_matrix(
        entries,
        tags={tag_id: _feature("tag", tag_id, "stressful-day")},
        symptoms={symptom_id: _feature("symptom", symptom_id, "headache")},
    )
    frame_without_sleep, meta_without_sleep = build_design_matrix(
        [
            _entry(entry.entry_date, tag_ids=entry.tag_ids, symptom_ids=entry.symptom_ids)
            for entry in entries
        ],
        tags={tag_id: _feature("tag", tag_id, "stressful-day")},
        symptoms={symptom_id: _feature("symptom", symptom_id, "headache")},
    )

    findings_with_sleep = run_lag_analysis(frame_with_sleep, meta_with_sleep)
    findings_without_sleep = run_lag_analysis(frame_without_sleep, meta_without_sleep)

    assert not any(finding.target.key == "sleep_minutes" for finding in findings_with_sleep)
    tag_symptom_finding = next(
        finding
        for finding in findings_with_sleep
        if finding.target.kind == "symptom" and finding.feature.kind == "tag"
    )
    # Match by lag_days too: adding sleep changes the FDR family, which can shift
    # *which* lag survives for tag/symptom — but not the sample size available at
    # any given lag, since a sparsely-recorded unrelated sleep column must not
    # shrink this pair's rows (that global-dropna regression is what #172 fixes).
    baseline_finding = next(
        finding
        for finding in findings_without_sleep
        if finding.target.kind == "symptom"
        and finding.feature.kind == "tag"
        and finding.lag_days == tag_symptom_finding.lag_days
    )
    assert tag_symptom_finding.sample_n == baseline_finding.sample_n


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


def test_lag_analysis_attaches_lag_profile() -> None:
    # #488 Phase 1b: each finding carries r at every observed lag for its pair.
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
    lag_finding = next(
        finding
        for finding in findings
        if finding.target.kind == "symptom" and finding.feature.kind == "tag"
    )

    lags = {point.lag_days for point in lag_finding.profile}
    # The profile spans multiple observed lags and includes the winning lag.
    assert len(lag_finding.profile) >= 2
    assert lag_finding.lag_days in lags
    assert all(isinstance(point.correlation, float) for point in lag_finding.profile)
    # Sorted by lag for stable rendering.
    assert [point.lag_days for point in lag_finding.profile] == sorted(lags)
