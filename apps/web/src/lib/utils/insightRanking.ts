import type { InsightResponse } from '$lib/api/insights';

export function insightPriorityScore(insight: InsightResponse): number {
  return (insight.confidence ?? 0) * Math.abs(insight.effect_size ?? 0);
}

export function rankInsights(insights: readonly InsightResponse[]): InsightResponse[] {
  return [...insights].sort((left, right) => {
    const scoreDelta = insightPriorityScore(right) - insightPriorityScore(left);
    if (scoreDelta !== 0) return scoreDelta;

    const generatedDelta = right.generated_at.localeCompare(left.generated_at);
    if (generatedDelta !== 0) return generatedDelta;

    return left.id.localeCompare(right.id);
  });
}
