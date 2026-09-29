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

/** Resolve the actual two endpoints before adding a temporal or associative glyph. */
export function insightEndpoints(insight: InsightResponse): { feature: string; target: string } {
  const payload = insight.payload ?? {};
  const label = (value: unknown): string | null => {
    if (!value || typeof value !== 'object') return null;
    const item = value as Record<string, unknown>;
    for (const key of ['label', 'key', 'id']) {
      if (typeof item[key] === 'string' && item[key]) return item[key] as string;
    }
    return null;
  };
  if (payload.method === 'lag') {
    return { feature: label(payload.feature) ?? '—', target: label(payload.target) ?? '—' };
  }
  if (payload.kind === 'symptom_tag_cooccurrence') {
    return {
      feature: typeof payload.symptom_name === 'string' ? payload.symptom_name : '—',
      target: typeof payload.tag_name === 'string' ? payload.tag_name : '—',
    };
  }
  return { feature: insight.subject_label ?? '—', target: insight.metric };
}
