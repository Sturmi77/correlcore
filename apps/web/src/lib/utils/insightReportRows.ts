import { insightEndpoints, insightRelation, relationPairLabel } from './insightRelation';
import { displayEffectForMetric } from './metrics';
import type { InsightResponse, InsightTier } from '$lib/api/insights';
import type { Translate } from './metricLabels';

/** Canonical row consumed by the report table and every export renderer. */
export interface InsightReportRow {
  id: string;
  factor: string | null;
  factorType: string | null;
  metric: string;
  target?: string;
  insightType: string;
  effect: number | null;
  displayEffect?: number | null;
  relationship?: string;
  relationGlyph?: string;
  confidence: number | null;
  sampleWith: number | null;
  sampleWithout: number | null;
  sampleTotal: number;
  tier: InsightTier;
  analysisWindowStart: string | null;
  analysisWindowEnd: string | null;
  generatedForDate: string | null;
  statement: string | null;
}

function finitePositive(payload: Record<string, unknown>, ...keys: string[]): number | null {
  for (const key of keys) {
    const value = payload[key];
    if (typeof value === 'number' && Number.isFinite(value) && value >= 0) return value;
  }
  return null;
}

function nonEmptyString(payload: Record<string, unknown>, ...keys: string[]): string | null {
  for (const key of keys) {
    const value = payload[key];
    if (typeof value === 'string' && value.trim()) return value;
  }
  return null;
}

export function toInsightReportRow(insight: InsightResponse, t?: Translate): InsightReportRow {
  const payload = insight.payload ?? {};
  const endpoints = insightEndpoints(insight, t);
  return {
    id: insight.id,
    factor: endpoints.feature,
    factorType: insight.subject_type,
    metric: insight.metric,
    target: endpoints.target,
    relationGlyph: insightRelation(insight).glyph,
    relationship: relationPairLabel(insight, endpoints.feature, endpoints.target),
    displayEffect:
      insight.effect_size === null
        ? null
        : displayEffectForMetric(insight.metric, insight.effect_size),
    insightType: insight.insight_type,
    effect: insight.effect_size,
    confidence: insight.confidence,
    sampleWith: finitePositive(payload, 'tagged_count', 'symptom_n', 'with_n'),
    sampleWithout: finitePositive(payload, 'untagged_count', 'comparison_n', 'without_n'),
    sampleTotal: insight.sample_n,
    tier: insight.tier,
    analysisWindowStart: nonEmptyString(payload, 'analysis_window_start', 'window_start'),
    analysisWindowEnd: nonEmptyString(payload, 'analysis_window_end', 'window_end'),
    generatedForDate: insight.generated_for_date || null,
    statement: insight.statement,
  };
}

export function buildInsightReportRows(
  insights: readonly InsightResponse[],
  t?: Translate
): InsightReportRow[] {
  return insights.map((insight) => toInsightReportRow(insight, t));
}

export function reportCoverageStats(rows: readonly InsightReportRow[]): {
  rowCount: number;
  maxSampleN: number;
} {
  return {
    rowCount: rows.length,
    maxSampleN: rows.reduce((largest, row) => Math.max(largest, row.sampleTotal), 0),
  };
}
