import type { InsightResponse } from '$lib/api/insights';
import { isCalendarContextConfounded } from './insightConfounder';

export function insightPriorityScore(insight: InsightResponse): number {
  return (insight.confidence ?? 0) * Math.abs(insight.effect_size ?? 0);
}

export function rankInsights(insights: readonly InsightResponse[]): InsightResponse[] {
  return [...insights].sort((left, right) => {
    const scoreDelta = insightPriorityScore(right) - insightPriorityScore(left);
    if (scoreDelta !== 0) return scoreDelta;

    const confoundDelta =
      Number(isCalendarContextConfounded(left)) - Number(isCalendarContextConfounded(right));
    if (confoundDelta !== 0) return confoundDelta;

    const generatedDelta = right.generated_at.localeCompare(left.generated_at);
    if (generatedDelta !== 0) return generatedDelta;

    return left.id.localeCompare(right.id);
  });
}
