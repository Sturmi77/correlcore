import { api } from './client';
import type { TagCategory } from './tags';

export type TimeseriesRange = 'week' | 'month' | 'quarter' | 'year';

export interface TimeseriesPoint {
  period_start: string;
  period_end: string;
  entry_count: number;
  mood_avg: number | null;
  energy_avg: number | null;
  stress_avg: number | null;
  sleep_quality_avg: number | null;
}

export interface TimeseriesResponse {
  range: TimeseriesRange;
  points: TimeseriesPoint[];
}

export interface TagHeatmapDay {
  date: string;
  count: number;
}

export interface TagHeatmapTag {
  tag_id: string;
  slug: string;
  name: string;
  category: TagCategory;
  color: string | null;
  days: TagHeatmapDay[];
}

export interface TagHeatmapResponse {
  start_date: string;
  end_date: string;
  tags: TagHeatmapTag[];
}

export interface SymptomHeatmapDay {
  date: string;
  count: number;
  max_intensity: number;
}

export interface SymptomHeatmapSymptom {
  symptom_id: string;
  slug: string;
  name: string;
  icon: string | null;
  days: SymptomHeatmapDay[];
}

export interface SymptomHeatmapResponse {
  start_date: string;
  end_date: string;
  symptoms: SymptomHeatmapSymptom[];
}

export interface EntryStreakResponse {
  current_streak: number;
  longest_streak: number;
  total_entry_days: number;
  last_entry_date: string | null;
  as_of: string;
}

export async function fetchTimeseries(range: TimeseriesRange): Promise<TimeseriesResponse> {
  return api.get<TimeseriesResponse>(`/entries/stats/timeseries?range=${range}`);
}

export async function fetchTagHeatmap(
  query: {
    start_date?: string;
    end_date?: string;
    category?: TagCategory;
  } = {}
): Promise<TagHeatmapResponse> {
  const params = new URLSearchParams();
  if (query.start_date) params.set('start_date', query.start_date);
  if (query.end_date) params.set('end_date', query.end_date);
  if (query.category) params.set('category', query.category);
  const qs = params.toString();
  return api.get<TagHeatmapResponse>(qs ? `/entries/stats/tags?${qs}` : '/entries/stats/tags');
}

export async function fetchSymptomHeatmap(
  query: {
    start_date?: string;
    end_date?: string;
  } = {}
): Promise<SymptomHeatmapResponse> {
  const params = new URLSearchParams();
  if (query.start_date) params.set('start_date', query.start_date);
  if (query.end_date) params.set('end_date', query.end_date);
  const qs = params.toString();
  return api.get<SymptomHeatmapResponse>(
    qs ? `/entries/stats/symptoms?${qs}` : '/entries/stats/symptoms'
  );
}

export async function fetchEntryStreak(asOf?: string): Promise<EntryStreakResponse> {
  const qs = asOf ? `?as_of=${encodeURIComponent(asOf)}` : '';
  return api.get<EntryStreakResponse>(`/entries/stats/streak${qs}`);
}
