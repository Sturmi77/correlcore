import type { InsightResponse } from '$lib/api/insights';

export const INSIGHTS_TOP_FINDING_PATH = '/insights';
export const TRENDS_COMPARE_PATH = '/trends';

export function topInsightLabel(insight: InsightResponse): string {
  return insight.subject_label?.trim() || insight.metric;
}
