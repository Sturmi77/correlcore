"""Symptom insight families: symptom↔metric and symptom↔tag co-occurrence.

Split out of ``insight_engine`` (#777); behavior is unchanged. The statistics
live in :mod:`app.services.symptom_analytics`; this module adapts analytics
rows and renders the persistence-ready candidates.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterable, Sequence
from datetime import date as date_type

from app.models.insight import InsightTier, InsightType
from app.services.insights.shared import (
    _METRIC_LABELS,
    AnalyticsEntry,
    InsightCandidate,
    SymptomSnapshot,
    TagSnapshot,
    _base_flags,
    _confidence,
    _confounders,
    _context_confounded_statement,
    _direction,
    _primary_confounder,
)
from app.services.symptom_analytics import (
    DailySymptomEntry,
    SymptomMetricAssociation,
    SymptomRef,
    SymptomTagAssociation,
    TagRef,
    compute_symptom_metric_associations,
    compute_symptom_tag_associations,
)


def _symptom_entries(entries: Sequence[AnalyticsEntry]) -> list[DailySymptomEntry]:
    return [
        DailySymptomEntry(
            entry_date=entry.entry_date,
            mood_score=entry.mood_score,
            energy=entry.energy,
            stress=entry.stress,
            tag_ids=entry.tag_ids,
            symptom_ids=entry.symptom_ids,
            work_context=entry.work_context,
        )
        for entry in entries
    ]


def _symptom_refs(symptoms: Iterable[SymptomSnapshot]) -> dict[uuid.UUID, SymptomRef]:
    return {
        symptom.id: SymptomRef(id=symptom.id, label=symptom.label, slug=symptom.slug)
        for symptom in symptoms
    }


def _tag_refs(tags: Iterable[TagSnapshot]) -> dict[uuid.UUID, TagRef]:
    return {tag.id: TagRef(id=tag.id, label=tag.label, slug=tag.slug) for tag in tags}


def _symptom_metric_statement(finding: SymptomMetricAssociation) -> str:
    direction = _direction(finding.coefficient, "higher", "lower")
    statement = (
        f"Days with {finding.symptom.label} currently line up with {direction} "
        f"{_METRIC_LABELS[finding.metric]} in your data."
    )
    return _context_confounded_statement(
        statement,
        weekday_confounded=finding.weekday_confounded,
        work_context_confounded=finding.work_context_confounded,
        calendar_context_confounded=finding.calendar_context_confounded,
    )


def _symptom_tag_statement(finding: SymptomTagAssociation) -> str:
    if finding.lift >= 1:
        relationship = "appears together with"
    else:
        relationship = "appears less often with"
    statement = (
        f"{finding.symptom.label} currently {relationship} {finding.tag.label} "
        "more than expected from their individual frequencies."
    )
    return _context_confounded_statement(
        statement,
        weekday_confounded=finding.weekday_confounded,
        work_context_confounded=finding.work_context_confounded,
        calendar_context_confounded=finding.calendar_context_confounded,
    )


def _symptom_metric_candidates(
    entries: Sequence[AnalyticsEntry],
    symptoms: Iterable[SymptomSnapshot],
    *,
    tier: InsightTier,
    generated_for_date: date_type,
) -> list[InsightCandidate]:
    findings = compute_symptom_metric_associations(
        _symptom_entries(entries),
        _symptom_refs(symptoms),
    )
    candidates: list[InsightCandidate] = []
    for finding in findings:
        confounders = _confounders(
            weekday_confounded=finding.weekday_confounded,
            work_context_confounded=finding.work_context_confounded,
            calendar_context_confounded=finding.calendar_context_confounded,
        )
        candidates.append(
            InsightCandidate(
                insight_type=InsightType.SYMPTOM_MOOD_ASSOCIATION,
                tier=tier,
                metric=finding.metric,
                subject_type="symptom",
                subject_id=finding.symptom.id,
                subject_label=finding.symptom.label,
                effect_size=finding.coefficient,
                confidence=_confidence(finding.coefficient, finding.p_corrected, tier),
                sample_n=finding.sample_n,
                statement=_symptom_metric_statement(finding),
                flags={
                    **_base_flags(
                        p_value=finding.p_value,
                        p_corrected=finding.p_corrected,
                        method="pointbiserial",
                    ),
                    "weekday_confounded": finding.weekday_confounded,
                    "work_context_confounded": finding.work_context_confounded,
                    "calendar_context_confounded": finding.calendar_context_confounded,
                    "min_symptom_usages": 5,
                },
                payload={
                    "kind": "symptom_mood_association",
                    "symptom_id": str(finding.symptom.id),
                    "symptom_slug": finding.symptom.slug,
                    "symptom_name": finding.symptom.label,
                    "metric": finding.metric,
                    "method": "pointbiserial",
                    "effect_size": finding.coefficient,
                    "p_value_corrected": finding.p_corrected,
                    "sample_n": finding.sample_n,
                    "symptom_n": finding.symptom_count,
                    "comparison_n": finding.comparison_count,
                    "symptom_metric_avg": finding.symptom_metric_avg,
                    "comparison_metric_avg": finding.comparison_metric_avg,
                    "confounder": _primary_confounder(confounders),
                    "confounders": confounders,
                },
                generated_for_date=generated_for_date,
            )
        )
    return candidates


def _symptom_tag_candidates(
    entries: Sequence[AnalyticsEntry],
    tags: Iterable[TagSnapshot],
    symptoms: Iterable[SymptomSnapshot],
    *,
    tier: InsightTier,
    generated_for_date: date_type,
) -> list[InsightCandidate]:
    findings = compute_symptom_tag_associations(
        _symptom_entries(entries),
        _symptom_refs(symptoms),
        _tag_refs(tags),
    )
    candidates: list[InsightCandidate] = []
    for finding in findings:
        effect_size = finding.phi if finding.phi != 0 else finding.lift - 1.0
        confounders = _confounders(
            weekday_confounded=finding.weekday_confounded,
            work_context_confounded=finding.work_context_confounded,
            calendar_context_confounded=finding.calendar_context_confounded,
        )
        candidates.append(
            InsightCandidate(
                insight_type=InsightType.SYMPTOM_TAG_COOCCURRENCE,
                tier=tier,
                metric="symptom_tag_cooccurrence",
                subject_type="symptom_tag",
                subject_id=None,
                subject_label=f"{finding.symptom.label} + {finding.tag.label}",
                effect_size=round(effect_size, 4),
                confidence=_confidence(effect_size, finding.p_corrected, tier),
                sample_n=finding.total_count,
                statement=_symptom_tag_statement(finding),
                flags={
                    **_base_flags(
                        p_value=finding.p_value,
                        p_corrected=finding.p_corrected,
                        method="fisher_exact_lift",
                    ),
                    "weekday_confounded": finding.weekday_confounded,
                    "work_context_confounded": finding.work_context_confounded,
                    "calendar_context_confounded": finding.calendar_context_confounded,
                    "min_symptom_usages": 5,
                    "min_tag_usages": 5,
                },
                payload={
                    "kind": "symptom_tag_cooccurrence",
                    "symptom_id": str(finding.symptom.id),
                    "symptom_slug": finding.symptom.slug,
                    "symptom_name": finding.symptom.label,
                    "tag_id": str(finding.tag.id),
                    "tag_slug": finding.tag.slug,
                    "tag_name": finding.tag.label,
                    "phi": finding.phi,
                    "jaccard": finding.jaccard,
                    "lift": finding.lift,
                    "co_count": finding.co_count,
                    "symptom_count": finding.symptom_count,
                    "tag_count": finding.tag_count,
                    "total_count": finding.total_count,
                    "p_value_corrected": finding.p_corrected,
                    "confounder": _primary_confounder(confounders),
                    "confounders": confounders,
                },
                generated_for_date=generated_for_date,
            )
        )
    return candidates
