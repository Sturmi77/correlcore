import { api } from './client';
import type { HabitType } from './tags';

export type HabitWindow = 7 | 14 | 28 | 90;
export type HabitTrendDirection = 'up' | 'down' | 'flat' | 'unknown';

export interface HabitStatsResponse {
  tag_id: string;
  habit_type: Exclude<HabitType, 'none'>;
  target_frequency: number;
  window: HabitWindow;
  start_date: string;
  end_date: string;
  days_tracked: number;
  days_total: number;
  target_days: number;
  adherence_rate: number;
  previous_adherence_rate: number | null;
  adherence_delta: number | null;
  trend_direction: HabitTrendDirection;
  correlation_score: number | null;
  correlation_metric: string | null;
}

export interface HabitListResponse {
  habits: HabitStatsResponse[];
}

export async function listHabits(window: HabitWindow = 28): Promise<HabitListResponse> {
  return api.get<HabitListResponse>(`/habits?window=${window}`);
}

export async function fetchHabitStats(
  tagId: string,
  window: HabitWindow = 28
): Promise<HabitStatsResponse> {
  return api.get<HabitStatsResponse>(`/habits/${tagId}/stats?window=${window}`);
}
