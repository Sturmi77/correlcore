import { describe, expect, it } from 'vitest';
import { displayMetricValue, displayTimeseriesValue } from './metrics';

describe('displayMetricValue', () => {
  it('passes mood and energy through unchanged', () => {
    expect(displayMetricValue('mood_score', 3)).toBe(3);
    expect(displayMetricValue('energy', 5)).toBe(5);
  });

  it('inverts stress on the 1–5 scale (6 - raw)', () => {
    expect(displayMetricValue('stress', 1)).toBe(5);
    expect(displayMetricValue('stress', 5)).toBe(1);
    expect(displayMetricValue('stress', 3)).toBe(3);
  });
});

describe('displayTimeseriesValue', () => {
  it('inverts stress_avg only', () => {
    expect(displayTimeseriesValue('mood_avg', 4)).toBe(4);
    expect(displayTimeseriesValue('stress_avg', 2)).toBe(4);
  });
});
