import { describe, expect, it } from 'vitest';
import { displayMetricAvg, visibleTrendDirection } from './metricTrend';
import type { MetricTrend } from '$lib/api/dashboard';

function trend(partial: Partial<MetricTrend>): MetricTrend {
  return {
    current_avg: 3.4,
    previous_avg: 3.0,
    current_n: 10,
    previous_n: 10,
    delta: 0.4,
    direction: 'up',
    ...partial,
  };
}

describe('metricTrend mapping', () => {
  it('prefers current_avg over the all-time value', () => {
    expect(displayMetricAvg(2.0, trend({ current_avg: 3.8 }))).toBe(3.8);
  });

  it('falls back to all-time only when the payload has no trend object', () => {
    expect(displayMetricAvg(2.0, null)).toBe(2.0);
    expect(displayMetricAvg(null, null)).toBeNull();
  });

  it('does not paint all-time as a window mean when current_avg is missing', () => {
    expect(displayMetricAvg(2.0, trend({ current_avg: null, direction: 'unknown' }))).toBeNull();
  });

  it('hides the glyph when direction is unknown or the trend is absent', () => {
    expect(visibleTrendDirection(trend({ direction: 'up' }))).toBe('up');
    expect(visibleTrendDirection(trend({ direction: 'flat' }))).toBe('flat');
    expect(visibleTrendDirection(trend({ direction: 'unknown' }))).toBeNull();
    expect(visibleTrendDirection(null)).toBeNull();
  });
});
