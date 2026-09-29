/**
 * Phase 7 / G2 helpers — with/without natural frequencies and distribution strips.
 */

import type { InsightResponse } from '$lib/api/insights';
import { displayMetricValue } from '$lib/utils/metrics';

export type WithWithoutView = {
  subjectLabel: string;
  withN: number;
  withoutN: number;
  withGood: number;
  withoutGood: number;
  withAvg: number | null;
  withoutAvg: number | null;
  withDistribution: number[] | null;
  withoutDistribution: number[] | null;
  goodThreshold: number;
  scaleMin: number;
  scaleMax: number;
  meanShift: number | null;
  isNullResult: boolean;
  overlap: 'low' | 'high' | 'unknown';
};

function asNumber(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

function asIntList(value: unknown, length: number, total: number): number[] | null {
  if (!Array.isArray(value) || value.length !== length) return null;
  const out: number[] = [];
  for (const item of value) {
    if (typeof item !== 'number' || !Number.isInteger(item) || item < 0) return null;
    out.push(item);
  }
  return out.reduce((sum, count) => sum + count, 0) === total ? out : null;
}

export function isWithWithoutInsight(insight: InsightResponse): boolean {
  return (
    insight.insight_type === 'pointbiserial' ||
    insight.insight_type === 'null_association' ||
    insight.insight_type === 'symptom_mood_association'
  );
}

export function isNullAssociation(insight: InsightResponse): boolean {
  if (insight.insight_type === 'null_association') return true;
  if (insight.flags?.non_result === true) return true;
  return insight.payload?.outcome === 'null';
}

/** Parse G2 fields from insight payload (pointbiserial / null / symptom mood). */
export function parseWithWithoutView(insight: InsightResponse): WithWithoutView | null {
  if (!isWithWithoutInsight(insight)) return null;
  const payload = insight.payload ?? {};
  const evidence = insight.evidence?.family === 'association' ? insight.evidence : null;
  const isSymptom = insight.insight_type === 'symptom_mood_association';

  const withN =
    evidence?.with_n ??
    asNumber(payload.tagged_count) ??
    asNumber(payload.symptom_n) ??
    asNumber(payload.with_n);
  const withoutN =
    evidence?.without_n ??
    asNumber(payload.untagged_count) ??
    asNumber(payload.comparison_n) ??
    asNumber(payload.without_n);
  if (
    withN == null ||
    withoutN == null ||
    !Number.isInteger(withN) ||
    !Number.isInteger(withoutN) ||
    withN <= 0 ||
    withoutN <= 0
  )
    return null;

  const scaleMin = asNumber(payload.scale_min) ?? 1;
  const scaleMax = asNumber(payload.scale_max) ?? 5;
  const levels = Math.max(1, Math.round(scaleMax - scaleMin) + 1);
  // A missing histogram is not an all-zero histogram. Substituting zeros made
  // every card whose payload lacked distributions claim "good on 0 of N days" —
  // a fabricated count presented as evidence (#928 L2). Absent distributions and
  // absent good-counts together mean there is nothing honest to render.
  const withDistribution = asIntList(
    evidence?.with_distribution ?? payload.with_distribution,
    levels,
    withN
  );
  const withoutDistribution = asIntList(
    evidence?.without_distribution ?? payload.without_distribution,
    levels,
    withoutN
  );
  const hasExplicitGoodCounts =
    (evidence?.with_good_count ?? asNumber(payload.with_good_count)) != null &&
    (evidence?.without_good_count ?? asNumber(payload.without_good_count)) != null;
  if ((withDistribution == null || withoutDistribution == null) && !hasExplicitGoodCounts) {
    return null;
  }
  const stress = insight.metric === 'stress';
  const rawThreshold = asNumber(payload.good_threshold) ?? (stress ? 2 : 4);
  const goodThreshold = stress ? displayMetricValue('stress', rawThreshold) : rawThreshold;
  const withLevels = stress ? (withDistribution?.slice().reverse() ?? null) : withDistribution;
  const withoutLevels = stress
    ? (withoutDistribution?.slice().reverse() ?? null)
    : withoutDistribution;
  const withGood =
    evidence?.with_good_count ??
    asNumber(payload.with_good_count) ??
    withLevels
      ?.slice(Math.max(0, Math.round(goodThreshold - scaleMin)))
      .reduce((sum, n) => sum + n, 0);
  const withoutGood =
    evidence?.without_good_count ??
    asNumber(payload.without_good_count) ??
    withoutLevels
      ?.slice(Math.max(0, Math.round(goodThreshold - scaleMin)))
      .reduce((sum, n) => sum + n, 0);
  if (
    withGood == null ||
    withoutGood == null ||
    !Number.isInteger(withGood) ||
    !Number.isInteger(withoutGood) ||
    withGood < 0 ||
    withoutGood < 0 ||
    withGood > withN ||
    withoutGood > withoutN
  )
    return null;

  const withAvg =
    evidence?.with_mean_raw ??
    asNumber(payload.tagged_mood_avg) ??
    asNumber(payload.symptom_metric_avg) ??
    asNumber(payload.with_mean);
  const withoutAvg =
    evidence?.without_mean_raw ??
    asNumber(payload.untagged_mood_avg) ??
    asNumber(payload.comparison_metric_avg) ??
    asNumber(payload.without_mean);

  const withDisplay =
    evidence?.with_mean_display ??
    (withAvg != null ? (stress ? displayMetricValue('stress', withAvg) : withAvg) : null);
  const withoutDisplay =
    evidence?.without_mean_display ??
    (withoutAvg != null ? (stress ? displayMetricValue('stress', withoutAvg) : withoutAvg) : null);
  const meanShift =
    withDisplay != null && withoutDisplay != null
      ? Math.round((withDisplay - withoutDisplay) * 10) / 10
      : null;

  const isNull = isNullAssociation(insight);
  const effect = insight.effect_size;
  let overlap: WithWithoutView['overlap'] = 'unknown';
  if (isNull || (effect != null && Math.abs(effect) < 0.25)) overlap = 'high';
  else if (effect != null && Math.abs(effect) >= 0.25) overlap = 'low';

  const subjectLabel =
    insight.subject_label ??
    (typeof payload.tag_slug === 'string'
      ? payload.tag_slug
      : typeof payload.symptom_name === 'string'
        ? payload.symptom_name
        : isSymptom
          ? 'symptom'
          : 'tag');

  return {
    subjectLabel,
    withN,
    withoutN,
    withGood,
    withoutGood,
    withAvg,
    withoutAvg,
    withDistribution: withLevels,
    withoutDistribution: withoutLevels,
    goodThreshold,
    scaleMin,
    scaleMax,
    meanShift,
    isNullResult: isNull,
    overlap,
  };
}
