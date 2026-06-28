import type { InsightResponse } from '$lib/api/insights';

/** True when backend marked a weekday confounder on payload or flags. */
export function isWeekdayConfounded(insight: InsightResponse): boolean {
  if (insight.payload?.confounder === 'weekday') return true;
  if (insight.flags?.weekday_confounded === true) return true;
  return false;
}
