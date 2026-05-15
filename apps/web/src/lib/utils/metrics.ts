import {
  ENTRY_METRICS,
  METRIC_SCALE_MAX,
  METRIC_SCALE_MIN,
  type EntryMetricField,
  type TimeseriesMetricKey,
  timeseriesMetricInvert,
} from '$lib/config/metrics';

/**
 * View-layer value for charts and sparklines (FRONTEND.md §4.3).
 * Raw storage and API payloads stay unchanged.
 */
export function displayMetricValue(
  field: EntryMetricField,
  raw: number,
  scaleMin = METRIC_SCALE_MIN,
  scaleMax = METRIC_SCALE_MAX,
): number {
  const def = ENTRY_METRICS[field];
  if (!def.invert) return raw;
  return scaleMin + scaleMax - raw;
}

export function displayTimeseriesValue(key: TimeseriesMetricKey, raw: number): number {
  if (!timeseriesMetricInvert(key)) return raw;
  return METRIC_SCALE_MIN + METRIC_SCALE_MAX - raw;
}
