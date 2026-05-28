/**
 * Canonical metric definitions — FRONTEND.md §4.3, M3.5 Sprint 2 (#182).
 *
 * Raw DB/API values are never mutated; use `displayMetricValue` for charts.
 */

import { ENTRY_CONTRACT } from '$lib/contracts/apiContract';
import type { EntryMetricField } from '$lib/contracts/apiContract';

export type { EntryMetricField } from '$lib/contracts/apiContract';

export type TimeseriesMetricKey = 'mood_avg' | 'energy_avg' | 'stress_avg';

export interface MetricDefinition {
  field: EntryMetricField;
  scaleMin: number;
  scaleMax: number;
  /** When true, higher raw values are worse; display uses `6 - raw` on 1–5 scale. */
  invert: boolean;
}

export const METRIC_SCALE_MIN = ENTRY_CONTRACT.metrics.mood_score.min;
export const METRIC_SCALE_MAX = ENTRY_CONTRACT.metrics.mood_score.max;

export const ENTRY_METRICS: Record<EntryMetricField, MetricDefinition> = {
  mood_score: {
    field: 'mood_score',
    scaleMin: ENTRY_CONTRACT.metrics.mood_score.min,
    scaleMax: ENTRY_CONTRACT.metrics.mood_score.max,
    invert: ENTRY_CONTRACT.metrics.mood_score.invert,
  },
  energy: {
    field: 'energy',
    scaleMin: ENTRY_CONTRACT.metrics.energy.min,
    scaleMax: ENTRY_CONTRACT.metrics.energy.max,
    invert: ENTRY_CONTRACT.metrics.energy.invert,
  },
  stress: {
    field: 'stress',
    scaleMin: ENTRY_CONTRACT.metrics.stress.min,
    scaleMax: ENTRY_CONTRACT.metrics.stress.max,
    invert: ENTRY_CONTRACT.metrics.stress.invert,
  },
  sleep_quality: {
    field: 'sleep_quality',
    scaleMin: ENTRY_CONTRACT.metrics.sleep_quality.min,
    scaleMax: ENTRY_CONTRACT.metrics.sleep_quality.max,
    invert: ENTRY_CONTRACT.metrics.sleep_quality.invert,
  },
  cycle_day: {
    field: 'cycle_day',
    scaleMin: ENTRY_CONTRACT.metrics.cycle_day.min,
    scaleMax: ENTRY_CONTRACT.metrics.cycle_day.max,
    invert: ENTRY_CONTRACT.metrics.cycle_day.invert,
  },
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
