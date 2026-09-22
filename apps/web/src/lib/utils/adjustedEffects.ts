import type { InsightResponse } from '$lib/api/insights';

export type AdjustedValue =
  { state: 'measured'; value: number } | { state: 'unavailable' } | { state: 'not_calculated' };

export type AdjustedEffectsView = {
  rawCorrelation: number | null;
  rawMeanDifference: number | null;
  weekday: AdjustedValue;
  calendar: AdjustedValue;
};

function finiteNumber(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

function adjustedValue(payload: Record<string, unknown>, key: string): AdjustedValue {
  if (!Object.prototype.hasOwnProperty.call(payload, key)) return { state: 'not_calculated' };
  const value = finiteNumber(payload[key]);
  return value === null ? { state: 'unavailable' } : { state: 'measured', value };
}

/** Only binary signal ↔ metric families have comparable adjusted OLS effects. */
export function parseAdjustedEffects(insight: InsightResponse): AdjustedEffectsView | null {
  if (
    insight.insight_type !== 'pointbiserial' &&
    insight.insight_type !== 'null_association' &&
    insight.insight_type !== 'symptom_mood_association'
  )
    return null;

  const payload = insight.payload ?? {};
  const withMean =
    finiteNumber(payload.tagged_mood_avg) ?? finiteNumber(payload.symptom_metric_avg);
  const withoutMean =
    finiteNumber(payload.untagged_mood_avg) ?? finiteNumber(payload.comparison_metric_avg);
  return {
    rawCorrelation: finiteNumber(insight.effect_size),
    rawMeanDifference: withMean !== null && withoutMean !== null ? withMean - withoutMean : null,
    weekday: adjustedValue(payload, 'weekday_held_coefficient'),
    calendar: adjustedValue(payload, 'calendar_held_coefficient'),
  };
}
