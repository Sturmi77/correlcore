import type { InsightResponse } from '$lib/api/insights';

export type InsightConfounder = 'weekday' | 'work_context' | 'calendar_context';

function isKnownConfounder(value: unknown): value is InsightConfounder {
  return value === 'weekday' || value === 'work_context' || value === 'calendar_context';
}

export function isCalendarContextInsight(insight: InsightResponse): boolean {
  return (
    insight.insight_type === 'weekday_pattern' ||
    insight.insight_type === 'work_context_pattern' ||
    insight.insight_type === 'weekday_context_pattern' ||
    insight.subject_type === 'weekday' ||
    insight.subject_type === 'work_context' ||
    typeof insight.payload?.weekday === 'number' ||
    typeof insight.payload?.work_context === 'string'
  );
}

/** Backend may mark one or several calendar/work-context confounders. */
export function getInsightConfounders(insight: InsightResponse): InsightConfounder[] {
  const values = new Set<InsightConfounder>();
  const payloadConfounder = insight.payload?.confounder;
  const payloadConfounders = insight.payload?.confounders;

  if (isKnownConfounder(payloadConfounder)) values.add(payloadConfounder);
  if (Array.isArray(payloadConfounders)) {
    payloadConfounders.forEach((value) => {
      if (isKnownConfounder(value)) values.add(value);
    });
  }
  if (insight.flags?.weekday_confounded === true) values.add('weekday');
  if (insight.flags?.work_context_confounded === true) values.add('work_context');
  if (insight.flags?.calendar_context_confounded === true) values.add('calendar_context');

  if (values.has('calendar_context')) return ['calendar_context'];
  return [...values];
}

export function primaryInsightConfounder(insight: InsightResponse): InsightConfounder | null {
  return getInsightConfounders(insight)[0] ?? null;
}

export function isCalendarContextConfounded(insight: InsightResponse): boolean {
  return getInsightConfounders(insight).length > 0;
}

/** True when backend marked a weekday confounder on payload or flags. */
export function isWeekdayConfounded(insight: InsightResponse): boolean {
  return getInsightConfounders(insight).includes('weekday');
}
