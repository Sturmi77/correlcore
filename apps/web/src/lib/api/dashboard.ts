import { api } from './client';
import type { InsightTier } from './insights';
import type { WorkContext } from './entries';

export interface WorkContextSummaryItem {
  work_context: WorkContext;
  entry_count: number;
  mood_avg: number | null;
  energy_avg: number | null;
  stress_avg: number | null;
}

/** Monday=0 … Sunday=6 (Python / backend convention). */
/** Most frequent signal on a weekday (#487). Descriptive, not causal. */
export interface WeekdayTopSignal {
  kind: 'tag' | 'symptom' | 'work_context';
  id: string | null;
  label: string;
  count: number;
  share: number;
}

export interface WeekdaySummaryItem {
  weekday: number;
  entry_count: number;
  mood_avg: number | null;
  top_signal?: WeekdayTopSignal | null;
}

export interface DashboardSummaryResponse {
  entry_count: number;
  insight_tier: InsightTier;
  confidence_score: number;
  work_context_summary: WorkContextSummaryItem[];
  weekday_summary: WeekdaySummaryItem[];
}

export async function fetchDashboardSummary(asOf?: string): Promise<DashboardSummaryResponse> {
  const qs = asOf ? `?as_of=${encodeURIComponent(asOf)}` : '';
  return api.get<DashboardSummaryResponse>(`/dashboard/summary${qs}`);
}
