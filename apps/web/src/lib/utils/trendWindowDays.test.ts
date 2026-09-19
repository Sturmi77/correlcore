import { describe, expect, it } from 'vitest';
import {
  coerceTrendWindowDays,
  isTrendWindowDays,
  timeseriesRangeToTrendWindowDays,
  trendWindowDaysToTimeseriesRange,
} from './trendWindowDays';

describe('trendWindowDays', () => {
  it('validates and coerces allowed values', () => {
    expect(isTrendWindowDays(14)).toBe(true);
    expect(isTrendWindowDays(7)).toBe(false);
    expect(coerceTrendWindowDays(90)).toBe(90);
    expect(coerceTrendWindowDays('28')).toBe(28);
    expect(coerceTrendWindowDays(7)).toBe(28);
  });

  it('maps to and from TimeseriesRange', () => {
    expect(trendWindowDaysToTimeseriesRange(14)).toBe('week');
    expect(trendWindowDaysToTimeseriesRange(28)).toBe('month');
    expect(trendWindowDaysToTimeseriesRange(90)).toBe('quarter');
    expect(timeseriesRangeToTrendWindowDays('week')).toBe(14);
    expect(timeseriesRangeToTrendWindowDays('month')).toBe(28);
    expect(timeseriesRangeToTrendWindowDays('quarter')).toBe(90);
    expect(timeseriesRangeToTrendWindowDays('year')).toBe(90);
  });
});
