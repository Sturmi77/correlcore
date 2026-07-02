import { describe, expect, it } from 'vitest';
import { analysisDateWindow, cooccurrenceRangeToTimeseries, timeseriesRangeToCooccurrence } from './analysisRange';

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

  it('builds calendar windows from the global analysis range', () => {
    const reference = new Date('2026-06-30T12:00:00');
    expect(analysisDateWindow('week', reference)).toEqual({
      start_date: '2026-06-24',
      end_date: '2026-06-30',
    });
    expect(analysisDateWindow('year', reference)).toEqual({
      start_date: '2025-07-01',
      end_date: '2026-06-30',
    });
  });
});
