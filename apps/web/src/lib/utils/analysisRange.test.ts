import { describe, expect, it } from 'vitest';
import {
  cooccurrenceRangeToTimeseries,
  timeseriesRangeToCooccurrence,
} from './analysisRange';

describe('analysisRange utils', () => {
  it('maps timeseries ranges to co-occurrence API windows', () => {
    expect(timeseriesRangeToCooccurrence('week')).toBe('30d');
    expect(timeseriesRangeToCooccurrence('month')).toBe('30d');
    expect(timeseriesRangeToCooccurrence('quarter')).toBe('90d');
    expect(timeseriesRangeToCooccurrence('year')).toBe('1y');
  });

  it('maps co-occurrence windows back to timeseries ranges', () => {
    expect(cooccurrenceRangeToTimeseries('30d')).toBe('month');
    expect(cooccurrenceRangeToTimeseries('90d')).toBe('quarter');
    expect(cooccurrenceRangeToTimeseries('1y')).toBe('year');
  });
});
