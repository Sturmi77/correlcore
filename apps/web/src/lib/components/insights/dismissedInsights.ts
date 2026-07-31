import type { InsightResponse } from '$lib/api/insights';

export interface DismissedInsightItem {
  dismissalId: string;
  insight: InsightResponse;
}
