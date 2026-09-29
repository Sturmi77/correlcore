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
  /** Phase 14 — optional duration series for Compare Zeitversatz. */
  sleep_minutes_avg?: number | null;
}

export interface TimeseriesResponse {
  range: TimeseriesRange;
  points: TimeseriesPoint[];
  /** Day buckets actually returned; set when an exact `days` window was requested. */
  days?: number | null;
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

// Health Data Maturity (Issue #852) — honest data-readiness / coverage panel.
// See docs/features/health-data-maturity.md. Not a physiological score.
export type HealthContextSectionId = 'symptom' | 'sleep';
export type HealthContextReason =
  'ok' | 'insufficient_entries' | 'insufficient_coverage' | 'no_consent';

export interface HealthContextMaturity {
  phase: string;
  phase_index: number;
  current_entries: number;
  next_phase_at: number | null;
  entries_until_next: number | null;
}

export interface CoverageMetric {
  days_with_data: number;
  window_days: number;
  pct: number;
}

export interface HealthContextCoverage {
  entry: CoverageMetric;
  sleep: CoverageMetric;
  symptom: CoverageMetric;
}

export interface HealthContextSection {
  id: HealthContextSectionId;
  unlocked: boolean;
  reason: HealthContextReason;
  entries_until_unlock: number | null;
  copy_key: string;
}

export interface HealthConnectStatus {
  consent: boolean;
  last_sync_at: string | null;
  sleep_import_ok: boolean | null;
}

export interface HealthContextResponse {
  as_of: string;
  coverage_window_days: number;
  maturity: HealthContextMaturity;
  coverage: HealthContextCoverage;
  sections: HealthContextSection[];
  health_connect: HealthConnectStatus | null;
}

/**
 * Daily aggregates for the analysis window.
 *
 * Pass `days` for the shared analysis window (14 | 28 | 90). The `range` enum
 * resolves to 7/30/90/365 server-side, so requesting 14 through it returned
 * seven days and 28 returned thirty — the chart then showed a different
 * population than its label claimed (#867). `range` stays for callers that
 * genuinely want a legacy bucket.
 */
export async function fetchTimeseries(
  range: TimeseriesRange,
  days?: number,
  options: { end_date?: string; signal?: AbortSignal } = {}
): Promise<TimeseriesResponse> {
  const query = new URLSearchParams({ range });
  if (days !== undefined) query.set('days', String(days));
  if (options.end_date) query.set('end_date', options.end_date);
  return api.get<TimeseriesResponse>(`/entries/stats/timeseries?${query}`, {
    signal: options.signal,
  });
}

export async function fetchTagHeatmap(
  query: {
    start_date?: string;
    end_date?: string;
    category?: TagCategory;
    /** Include visible tags with `include_in_analytics=false` (entry-form recency cloud, #898). */
    include_non_analytics?: boolean;
  } = {}
): Promise<TagHeatmapResponse> {
  const params = new URLSearchParams();
  if (query.start_date) params.set('start_date', query.start_date);
  if (query.end_date) params.set('end_date', query.end_date);
  if (query.category) params.set('category', query.category);
  if (query.include_non_analytics) params.set('include_non_analytics', 'true');
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

export async function fetchHealthContext(asOf?: string): Promise<HealthContextResponse> {
  const qs = asOf ? `?as_of=${encodeURIComponent(asOf)}` : '';
  return api.get<HealthContextResponse>(`/entries/stats/health-context${qs}`);
}
