import type { HabitWindow } from '$lib/api/habits';
import type { TimeseriesRange } from '$lib/api/stats';

const RANGE_DAYS: Record<TimeseriesRange, number> = {
  week: 7,
  month: 30,
  quarter: 90,
  year: 365,
};

/** localStorage key for Raw | Smoothed preference (ADR-0029). */
export const TREND_SMOOTHING_STORAGE_KEY = 'cc_trend_smooth';

export function rangeToDays(range: TimeseriesRange): number {
  return RANGE_DAYS[range];
}

/**
 * Trailing SMA window for the compare timeline.
 * Week keeps a short 3-day window so daily shape stays readable; longer
 * ranges use the classic 7-day SMA from ADR-0029.
 */
export function smoothingWindowDays(range: TimeseriesRange): number {
  return range === 'week' ? 3 : 7;
}

/**
 * Resolve persisted Raw/Smoothed preference. Missing key → default on
 * (smoothed), so new sessions and upgrades land on the softer trend.
 */
export function readSmoothingPreference(
  storage: Pick<Storage, 'getItem'> | null | undefined,
  fallback = true
): boolean {
  const raw = storage?.getItem(TREND_SMOOTHING_STORAGE_KEY);
  if (raw === 'true') return true;
  if (raw === 'false') return false;
  return fallback;
}

/** Map the global Trends range to the closest supported habit review window. */
export function rangeToHabitWindow(range: TimeseriesRange): HabitWindow {
  switch (range) {
    case 'week':
      return 7;
    case 'month':
      return 28;
    case 'quarter':
    case 'year':
      return 90;
    default:
      return 28;
  }
}
