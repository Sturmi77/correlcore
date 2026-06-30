import type { HabitWindow } from '$lib/api/habits';
import type { TimeseriesRange } from '$lib/api/stats';

const RANGE_DAYS: Record<TimeseriesRange, number> = {
  week: 7,
  month: 30,
  quarter: 90,
  year: 365,
};

export function rangeToDays(range: TimeseriesRange): number {
  return RANGE_DAYS[range];
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
