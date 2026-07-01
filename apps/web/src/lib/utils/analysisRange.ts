import type { TagCooccurrenceRange } from '$lib/api/insights';
import type { TimeseriesRange } from '$lib/api/stats';

export const ANALYSIS_RANGE_OPTIONS: TimeseriesRange[] = ['week', 'month', 'quarter', 'year'];

const VALID_RANGES = new Set<TimeseriesRange>(ANALYSIS_RANGE_OPTIONS);

export function isTimeseriesRange(value: string): value is TimeseriesRange {
  return VALID_RANGES.has(value as TimeseriesRange);
}

/** Map the global Trends range to the closest Insights co-occurrence API window. */
export function timeseriesRangeToCooccurrence(range: TimeseriesRange): TagCooccurrenceRange {
  switch (range) {
    case 'quarter':
      return '90d';
    case 'year':
      return '1y';
    case 'week':
    case 'month':
    default:
      return '30d';
  }
}

/** Reverse map for migrating legacy co-occurrence-only preferences. */
export function cooccurrenceRangeToTimeseries(range: TagCooccurrenceRange): TimeseriesRange {
  switch (range) {
    case '90d':
      return 'quarter';
    case '1y':
      return 'year';
    case '30d':
    default:
      return 'month';
  }
}
