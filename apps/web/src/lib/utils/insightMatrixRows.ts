/**
 * Shared matrix row derivation for InsightMatrix (hub) and /insights/report
 * (Phase 5 / Ebene 4). Keeps strong/weak banding and dedupe in one place.
 */

import type { InsightResponse } from '$lib/api/insights';
import { isMatrixInsight, isWeakMatrixInsight } from '$lib/utils/insightMatrixGate';

export type MatrixTone = 'positive' | 'negative' | 'neutral';

export type MatrixDisplayRows = {
  strong: InsightResponse[];
  weak: InsightResponse[];
  all: InsightResponse[];
};

function canonicalMetric(insight: InsightResponse): string {
  if (
    insight.subject_type === 'tag' &&
    ['mood', 'mood_score', 'mood_avg'].includes(insight.metric)
  ) {
    return 'mood_score';
  }
  return insight.metric;
}

function normaliseLabel(value: string): string {
  return value.toLocaleLowerCase().trim().replace(/\s+/g, ' ');
}

export function matrixRowKey(insight: InsightResponse): string {
  const tagSlug =
    typeof insight.payload?.tag_slug === 'string' ? normaliseLabel(insight.payload.tag_slug) : '';
  const subject =
    insight.subject_type === 'tag'
      ? tagSlug ||
        (insight.subject_label ? normaliseLabel(insight.subject_label) : '') ||
        insight.subject_id ||
        ''
      : insight.subject_id || insight.subject_label || '';
  return [insight.insight_type, canonicalMetric(insight), insight.subject_type ?? '', subject].join(
    ':'
  );
}

function strongerRow(left: InsightResponse, right: InsightResponse): InsightResponse {
  const leftEffect = Math.abs(left.effect_size ?? 0);
  const rightEffect = Math.abs(right.effect_size ?? 0);
  if (leftEffect !== rightEffect) return leftEffect > rightEffect ? left : right;
  const leftConfidence = left.confidence ?? 0;
  const rightConfidence = right.confidence ?? 0;
  if (leftConfidence !== rightConfidence) return leftConfidence > rightConfidence ? left : right;
  return left.generated_at >= right.generated_at ? left : right;
}

export function dedupeMatrixRows(items: readonly InsightResponse[]): InsightResponse[] {
  const byKey = new Map<string, InsightResponse>();
  for (const insight of items) {
    const key = matrixRowKey(insight);
    const existing = byKey.get(key);
    byKey.set(key, existing ? strongerRow(existing, insight) : insight);
  }
  return [...byKey.values()];
}

function byEffectDesc(a: InsightResponse, b: InsightResponse): number {
  return Math.abs(b.effect_size ?? 0) - Math.abs(a.effect_size ?? 0);
}

/** Strong + weak bands after family filter and dedupe (preview drops weak). */
export function buildMatrixDisplayRows(
  insights: readonly InsightResponse[],
  options?: { includeWeak?: boolean }
): MatrixDisplayRows {
  const includeWeak = options?.includeWeak ?? true;
  const displayRows = dedupeMatrixRows(
    insights.filter((insight) => isMatrixInsight(insight) || isWeakMatrixInsight(insight))
  );
  const strong = displayRows.filter(isMatrixInsight).sort(byEffectDesc);
  const weak = includeWeak ? displayRows.filter(isWeakMatrixInsight).sort(byEffectDesc) : [];
  return { strong, weak, all: [...strong, ...weak] };
}

export function matrixEffectTone(effect: number): MatrixTone {
  if (effect >= 0.15) return 'positive';
  if (effect <= -0.15) return 'negative';
  return 'neutral';
}

export function matrixConfidencePercent(value: number | null): string {
  if (value === null) return '-';
  return `${Math.round(value * 100)}%`;
}

/** Coverage line for the report footer (aggregated, no single-day rows). */
export function matrixCoverageStats(rows: readonly InsightResponse[]): {
  rowCount: number;
  maxSampleN: number;
} {
  let maxSampleN = 0;
  for (const row of rows) {
    if (row.sample_n > maxSampleN) maxSampleN = row.sample_n;
  }
  return { rowCount: rows.length, maxSampleN };
}
