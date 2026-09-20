/**
 * Phase 7 / G2 helpers — with/without natural frequencies and distribution strips.
 */

import type { InsightResponse } from '$lib/api/insights';

export type WithWithoutView = {
  subjectLabel: string;
  withN: number;
  withoutN: number;
  withGood: number;
  withoutGood: number;
  withAvg: number | null;
  withoutAvg: number | null;
  withDistribution: number[];
  withoutDistribution: number[];
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

function asIntList(value: unknown, length: number): number[] | null {
  if (!Array.isArray(value) || value.length !== length) return null;
  const out: number[] = [];
  for (const item of value) {
    if (typeof item !== 'number' || !Number.isFinite(item) || item < 0) return null;
    out.push(Math.round(item));
  }
  return out;
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
  const isSymptom = insight.insight_type === 'symptom_mood_association';

  const withN =
    asNumber(payload.tagged_count) ?? asNumber(payload.symptom_n) ?? asNumber(payload.with_n);
  const withoutN =
    asNumber(payload.untagged_count) ??
    asNumber(payload.comparison_n) ??
    asNumber(payload.without_n);
  if (withN == null || withoutN == null || withN <= 0 || withoutN <= 0) return null;

  const scaleMin = asNumber(payload.scale_min) ?? 1;
  const scaleMax = asNumber(payload.scale_max) ?? 5;
  const levels = Math.max(1, Math.round(scaleMax - scaleMin) + 1);
  // A missing histogram is not an all-zero histogram. Substituting zeros made
  // every card whose payload lacked distributions claim "good on 0 of N days" —
  // a fabricated count presented as evidence (#928 L2). Absent distributions and
  // absent good-counts together mean there is nothing honest to render.
  const withDistribution = asIntList(payload.with_distribution, levels);
  const withoutDistribution = asIntList(payload.without_distribution, levels);
  const hasExplicitGoodCounts =
    asNumber(payload.with_good_count) != null && asNumber(payload.without_good_count) != null;
  if ((withDistribution == null || withoutDistribution == null) && !hasExplicitGoodCounts) {
    return null;
  }
  const withLevels = withDistribution ?? Array.from({ length: levels }, () => 0);
  const withoutLevels = withoutDistribution ?? Array.from({ length: levels }, () => 0);

  const goodThreshold = asNumber(payload.good_threshold) ?? 4;
  const withGood =
    asNumber(payload.with_good_count) ??
    withLevels
      .slice(Math.max(0, Math.round(goodThreshold - scaleMin)))
      .reduce((sum, n) => sum + n, 0);
  const withoutGood =
    asNumber(payload.without_good_count) ??
    withoutLevels
      .slice(Math.max(0, Math.round(goodThreshold - scaleMin)))
      .reduce((sum, n) => sum + n, 0);

  const withAvg =
    asNumber(payload.tagged_mood_avg) ??
    asNumber(payload.symptom_metric_avg) ??
    asNumber(payload.with_mean);
  const withoutAvg =
    asNumber(payload.untagged_mood_avg) ??
    asNumber(payload.comparison_metric_avg) ??
    asNumber(payload.without_mean);

  const meanShift =
    withAvg != null && withoutAvg != null ? Math.round((withAvg - withoutAvg) * 10) / 10 : null;

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
