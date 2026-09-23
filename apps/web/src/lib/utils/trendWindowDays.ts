/**
 * Shared analysis window (#867): 14 | 28 | 90 days.
 * Maps to TimeseriesRange only where the stats API still expects an enum.
 */
import type { TimeseriesRange } from '$lib/api/stats';
import type { TagCooccurrenceRange } from '$lib/api/insights';

export const TREND_WINDOW_DAYS_OPTIONS = [14, 28, 90] as const;
export type TrendWindowDays = (typeof TREND_WINDOW_DAYS_OPTIONS)[number];
export const TREND_WINDOW_DAYS_DEFAULT: TrendWindowDays = 28;

export function isTrendWindowDays(value: unknown): value is TrendWindowDays {
  return value === 14 || value === 28 || value === 90;
}

export function coerceTrendWindowDays(value: unknown): TrendWindowDays {
  if (typeof value === 'number' && isTrendWindowDays(value)) return value;
  if (typeof value === 'string') {
    const parsed = Number(value);
    if (isTrendWindowDays(parsed)) return parsed;
  }
  return TREND_WINDOW_DAYS_DEFAULT;
}

/** Map preference days → closest TimeseriesRange for `/entries/stats/timeseries`. */
export function trendWindowDaysToTimeseriesRange(days: TrendWindowDays): TimeseriesRange {
  if (days === 14) return 'week';
  if (days === 90) return 'quarter';
  return 'month';
}

/** Exact co-occurrence window for the shared analysis preference. */
export function trendWindowDaysToCooccurrence(days: TrendWindowDays): TagCooccurrenceRange {
  if (days === 14) return '14d';
  if (days === 90) return '90d';
  return '28d';
}

/** Map legacy TimeseriesRange chips → preference days (year collapses to 90). */
export function timeseriesRangeToTrendWindowDays(range: TimeseriesRange): TrendWindowDays {
  if (range === 'week') return 14;
  if (range === 'quarter' || range === 'year') return 90;
  return 28;
}
