import type { MetricTrend, MetricTrendDirection } from '$lib/api/dashboard';

export type VisibleTrendDirection = Exclude<MetricTrendDirection, 'unknown'>;

/**
 * Window mean when the backend sent one.
 * A live `MetricTrend` with no `current_avg` is an empty window, not all-time.
 * All-time is only used for legacy payloads that omit `trend` entirely.
 */
export function displayMetricAvg(
  allTime: number | null | undefined,
  trend: MetricTrend | null | undefined
): number | null {
  if (typeof trend?.current_avg === 'number' && Number.isFinite(trend.current_avg)) {
    return trend.current_avg;
  }
  if (trend) {
    return null;
  }
  return typeof allTime === 'number' && Number.isFinite(allTime) ? allTime : null;
}

/** Glyph direction, or null when the indicator must be omitted. */
export function visibleTrendDirection(
  trend: MetricTrend | null | undefined
): VisibleTrendDirection | null {
  if (!trend) return null;
  if (trend.direction === 'unknown') return null;
  return trend.direction;
}
