import type { InsightResponse } from '$lib/api/insights';

/** Insights eligible for the correlation matrix (matches InsightMatrix filter). */
export function isMatrixInsight(insight: InsightResponse): boolean {
  return (
    (insight.insight_type === 'pointbiserial' ||
      insight.insight_type === 'symptom_mood_association') &&
    insight.effect_size !== null &&
    insight.confidence !== null &&
    insight.confidence >= 0.2
  );
}

export function countMatrixInsights(insights: readonly InsightResponse[]): number {
  return insights.filter(isMatrixInsight).length;
}

/** Matrix tab is shown when at least two pointbiserial-style insights exist. */
export const MATRIX_TAB_MIN_INSIGHTS = 2;
