"""Multivariate insight families: LASSO signal ranking and lagged associations.

Split out of ``insight_engine`` (#777); behavior is unchanged. The heavy
statistics live in :mod:`app.services.multivariate_analytics`; this module
adapts analytics rows into design-matrix inputs and renders the candidates.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterable, Sequence
from datetime import date as date_type

from app.models.insight import InsightTier, InsightType
from app.services.insights.shared import (
    AnalyticsEntry,
    InsightCandidate,
    SymptomSnapshot,
    TagSnapshot,
    _base_flags,
    _confidence,
    _direction,
)
from app.services.multivariate_analytics import (
    FeatureMetadata,
    LagFinding,
    LassoFinding,
    MultivariateEntry,
    build_design_matrix,
    run_lag_analysis,
    run_lasso_models,
)


def _multivariate_entries(entries: Sequence[AnalyticsEntry]) -> list[MultivariateEntry]:
    return [
        MultivariateEntry(
            entry_date=entry.entry_date,
            mood_score=entry.mood_score,
            energy=entry.energy,
            stress=entry.stress,
            tag_ids=entry.tag_ids,
            symptom_ids=entry.symptom_ids,
            sleep_minutes=entry.sleep_minutes,
            sleep_quality=entry.sleep_quality,
        )
        for entry in entries
    ]


def _feature_meta_for_tags(tags: Iterable[TagSnapshot]) -> dict[uuid.UUID, FeatureMetadata]:
    return {
        tag.id: FeatureMetadata(
            kind="tag",
            key=f"tag:{tag.slug}",
            label=tag.label,
            slug=tag.slug,
            id=tag.id,
        )
        for tag in tags
    }


def _feature_meta_for_symptoms(
    symptoms: Iterable[SymptomSnapshot],
) -> dict[uuid.UUID, FeatureMetadata]:
    return {
        symptom.id: FeatureMetadata(
            kind="symptom",
            key=f"symptom:{symptom.slug}",
            label=symptom.label,
            slug=symptom.slug,
            id=symptom.id,
        )
        for symptom in symptoms
    }


def _payload_feature(
    feature: FeatureMetadata, *, coefficient: float | None = None
) -> dict[str, object]:
    payload: dict[str, object] = {
        "kind": feature.kind,
        "key": feature.key,
        "name": feature.label,
    }
    if feature.slug is not None:
        payload["slug"] = feature.slug
    if feature.id is not None:
        payload["id"] = str(feature.id)
    if coefficient is not None:
        payload["coefficient"] = coefficient
    return payload


def _lasso_statement(finding: LassoFinding) -> str:
    labels = ", ".join(feature.feature.label for feature in finding.features[:3])
    return f"Across your tracked signals, {finding.target} currently varies most with {labels}."


def _lag_statement(finding: LagFinding) -> str:
    direction = _direction(finding.correlation, "higher", "lower")
    return (
        f"{finding.feature.label} logged {finding.lag_days} day(s) earlier currently lines up "
        f"with {direction} {finding.target.label}."
    )


def _lasso_candidates(
    entries: Sequence[AnalyticsEntry],
    tags: Iterable[TagSnapshot],
    symptoms: Iterable[SymptomSnapshot],
    *,
    tier: InsightTier,
    generated_for_date: date_type,
) -> list[InsightCandidate]:
    frame, feature_meta = build_design_matrix(
        _multivariate_entries(entries),
        tags=_feature_meta_for_tags(tags),
        symptoms=_feature_meta_for_symptoms(symptoms),
    )
    findings = run_lasso_models(frame, feature_meta)
    candidates: list[InsightCandidate] = []
    for finding in findings:
        max_coefficient = max(abs(feature.coefficient) for feature in finding.features)
        candidates.append(
            InsightCandidate(
                insight_type=InsightType.SYMPTOM_CLUSTER,
                tier=tier,
                metric=finding.target,
                subject_type="metric",
                subject_id=None,
                subject_label=finding.target,
                effect_size=round(max_coefficient, 4),
                confidence=_confidence(max_coefficient, None, tier),
                sample_n=finding.sample_n,
                statement=_lasso_statement(finding),
                flags=_base_flags(p_value=None, method="lasso"),
                payload={
                    "method": "lasso",
                    "target": finding.target,
                    "features": [
                        _payload_feature(feature.feature, coefficient=feature.coefficient)
                        for feature in finding.features
                    ],
                    "cv": "TimeSeriesSplit",
                    "cv_splits": 5,
                    "cv_score": finding.cv_score,
                    "alpha": finding.alpha,
                    "sample_n": finding.sample_n,
                },
                generated_for_date=generated_for_date,
            )
        )
    return candidates


def _lag_candidates(
    entries: Sequence[AnalyticsEntry],
    tags: Iterable[TagSnapshot],
    symptoms: Iterable[SymptomSnapshot],
    *,
    tier: InsightTier,
    generated_for_date: date_type,
) -> list[InsightCandidate]:
    frame, feature_meta = build_design_matrix(
        _multivariate_entries(entries),
        tags=_feature_meta_for_tags(tags),
        symptoms=_feature_meta_for_symptoms(symptoms),
    )
    findings = run_lag_analysis(frame, feature_meta)
    candidates: list[InsightCandidate] = []
    for finding in findings:
        target_id = finding.target.id if finding.target.kind == "symptom" else None
        metric = finding.target.key if finding.target.kind == "metric" else "symptom_presence"
        candidates.append(
            InsightCandidate(
                insight_type=InsightType.SYMPTOM_CLUSTER,
                tier=tier,
                metric=metric,
                subject_type=finding.target.kind,
                subject_id=target_id,
                subject_label=finding.target.label,
                effect_size=finding.correlation,
                confidence=_confidence(finding.correlation, finding.p_corrected, tier),
                sample_n=finding.sample_n,
                statement=_lag_statement(finding),
                flags={
                    **_base_flags(
                        p_value=finding.p_value,
                        p_corrected=finding.p_corrected,
                        method="lag",
                    ),
                    "lag_days": finding.lag_days,
                },
                payload={
                    "method": "lag",
                    "target": _payload_feature(finding.target),
                    "feature": _payload_feature(finding.feature),
                    "lag_days": finding.lag_days,
                    "correlation": finding.correlation,
                    "p_value_corrected": finding.p_corrected,
                    "sample_n": finding.sample_n,
                    # #488 Phase 1b: r at each observed lag 1..7 for the mini profile.
                    "lag_profile": [
                        {"lag": point.lag_days, "r": point.correlation} for point in finding.profile
                    ],
                },
                generated_for_date=generated_for_date,
            )
        )
    return candidates
