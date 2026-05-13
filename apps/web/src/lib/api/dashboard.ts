import { api } from './client';
import type { InsightTier } from './insights';

export interface DashboardSummaryResponse {
  entry_count: number;
  insight_tier: InsightTier;
  confidence_score: number;
}

export async function fetchDashboardSummary(asOf?: string): Promise<DashboardSummaryResponse> {
  const qs = asOf ? `?as_of=${encodeURIComponent(asOf)}` : '';
  return api.get<DashboardSummaryResponse>(`/dashboard/summary${qs}`);
}
