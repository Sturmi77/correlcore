/**
 * Canonical metric definitions — FRONTEND.md §4.3, M3.5 Sprint 2 (#182).
 *
 * Raw DB/API values are never mutated; use `displayMetricValue` for charts.
 */

export type EntryMetricField = 'mood_score' | 'energy' | 'stress' | 'sleep_quality';

export type TimeseriesMetricKey = 'mood_avg' | 'energy_avg' | 'stress_avg';

export interface MetricDefinition {
  field: EntryMetricField;
  scaleMin: number;
  scaleMax: number;
  /** When true, higher raw values are worse; display uses `6 - raw` on 1–5 scale. */
  invert: boolean;
}

export const METRIC_SCALE_MIN = 1;
export const METRIC_SCALE_MAX = 5;

export const ENTRY_METRICS: Record<EntryMetricField, MetricDefinition> = {
  mood_score: { field: 'mood_score', scaleMin: 1, scaleMax: 5, invert: false },
  energy: { field: 'energy', scaleMin: 1, scaleMax: 5, invert: false },
  stress: { field: 'stress', scaleMin: 1, scaleMax: 5, invert: true },
  sleep_quality: { field: 'sleep_quality', scaleMin: 1, scaleMax: 5, invert: false },
};

/** Maps timeseries API keys to entry metric fields. */
export const TIMESERIES_METRIC_FIELDS: Record<TimeseriesMetricKey, EntryMetricField> = {
  mood_avg: 'mood_score',
  energy_avg: 'energy',
  stress_avg: 'stress',
};

export function getEntryMetric(field: EntryMetricField): MetricDefinition {
  return ENTRY_METRICS[field];
}

export function timeseriesMetricInvert(key: TimeseriesMetricKey): boolean {
  return ENTRY_METRICS[TIMESERIES_METRIC_FIELDS[key]].invert;
}
