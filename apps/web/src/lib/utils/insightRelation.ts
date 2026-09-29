import type { InsightResponse } from '$lib/api/insights';

export type InsightRelation = {
  glyph: '↔' | '→' | '←';
  lagDays: number | null;
};

/** A temporal arrow requires an actual signed lag, not merely a correlation. */
export function insightRelation(insight: InsightResponse): InsightRelation {
  const lag = insight.payload?.lag_days ?? insight.flags?.lag_days;
  const temporal =
    insight.payload?.method === 'lag' ||
    (insight.insight_type === 'symptom_cluster' && insight.flags?.method === 'lag');
  if (!temporal || typeof lag !== 'number' || !Number.isSafeInteger(lag)) {
    return { glyph: '↔', lagDays: null };
  }
  return { glyph: lag > 0 ? '→' : lag < 0 ? '←' : '↔', lagDays: lag };
}

export function relationPairLabel(
  insight: InsightResponse,
  feature: string,
  target: string
): string {
  const relation = insightRelation(insight);
  const offset =
    relation.lagDays === null ? '' : ` (${relation.lagDays > 0 ? '+' : ''}${relation.lagDays}d)`;
  return `${feature} ${relation.glyph} ${target}${offset}`;
}
