import type { TagCooccurrenceRange } from '$lib/api/insights';
import type { TimeseriesRange } from '$lib/api/stats';
import { localIsoDate, shiftIsoDate } from '$lib/utils/streak';
import { rangeToDays } from '$lib/utils/trendsRange';

export const ANALYSIS_RANGE_OPTIONS: TimeseriesRange[] = ['week', 'month', 'quarter', 'year'];

const VALID_RANGES = new Set<TimeseriesRange>(ANALYSIS_RANGE_OPTIONS);

export function isTimeseriesRange(value: string): value is TimeseriesRange {
  return VALID_RANGES.has(value as TimeseriesRange);
}

/** Map the global Trends range to the closest Insights co-occurrence API window. */
export function timeseriesRangeToCooccurrence(range: TimeseriesRange): TagCooccurrenceRange {
  switch (range) {
    case 'week':
      return '7d';
    case 'quarter':
      return '90d';
    case 'year':
      return '1y';
    case 'month':
    default:
      return '30d';
  }
}

/** Reverse map for migrating legacy co-occurrence-only preferences. */
/** Calendar window for symptom heatmaps and entry-backed analytics. */
export function analysisDateWindow(
  range: TimeseriesRange,
  referenceDate: Date = new Date()
): { start_date: string; end_date: string } {
  const end_date = localIsoDate(referenceDate);
  const windowDays = rangeToDays(range);
  return { start_date: shiftIsoDate(end_date, -(windowDays - 1)), end_date };
}

export function cooccurrenceRangeToTimeseries(range: TagCooccurrenceRange): TimeseriesRange {
  switch (range) {
    case '7d':
      return 'week';
    case '90d':
      return 'quarter';
    case '1y':
      return 'year';
    case '30d':
    default:
      return 'month';
  }
}
