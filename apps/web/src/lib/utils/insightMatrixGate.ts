import type { InsightResponse } from '$lib/api/insights';

/** Confidence at/above which a correlation is shown as a reliable matrix row. */
export const MATRIX_STRONG_MIN_CONFIDENCE = 0.2;
/**
 * Confidence floor for "weakened" rows (#725). Correlations between this and the
 * strong threshold are no longer hidden outright — they move into a collapsible
 * "weaker correlations" section instead of making the matrix disappear.
 */
export const MATRIX_WEAK_MIN_CONFIDENCE = 0.1;

/** Insight families that populate the correlation matrix. */
function isMatrixFamily(insight: InsightResponse): boolean {
  return (
    insight.insight_type === 'pointbiserial' || insight.insight_type === 'symptom_mood_association'
  );
}

/** Reliable matrix rows: matrix family with confidence at/above the strong floor. */
export function isMatrixInsight(insight: InsightResponse): boolean {
  return (
    isMatrixFamily(insight) &&
    insight.effect_size !== null &&
    insight.confidence !== null &&
    insight.confidence >= MATRIX_STRONG_MIN_CONFIDENCE
  );
}

/**
 * Weakened matrix rows (#725): matrix family whose confidence sits in the
 * [weak, strong) band. Shown collapsed rather than dropped, so a run that only
 * softened an existing correlation no longer makes the matrix vanish.
 */
export function isWeakMatrixInsight(insight: InsightResponse): boolean {
  return (
    isMatrixFamily(insight) &&
    insight.effect_size !== null &&
    insight.confidence !== null &&
    insight.confidence >= MATRIX_WEAK_MIN_CONFIDENCE &&
    insight.confidence < MATRIX_STRONG_MIN_CONFIDENCE
  );
}

/** Count of reliable (strong) matrix insights. */
export function countMatrixInsights(insights: readonly InsightResponse[]): number {
  return insights.filter(isMatrixInsight).length;
}

/** Count of everything the matrix can render — reliable plus weakened rows. */
export function countDisplayableMatrixInsights(insights: readonly InsightResponse[]): number {
  return insights.filter((insight) => isMatrixInsight(insight) || isWeakMatrixInsight(insight))
    .length;
}

/** Matrix section is shown when at least two renderable pointbiserial-style rows exist. */
export const MATRIX_TAB_MIN_INSIGHTS = 2;
