import { describe, expect, it } from 'vitest';
import type { TimeseriesPoint } from '$lib/api/stats';
import { applySleepZeitversatz } from './sleepZeitversatz';

function point(
  date: string,
  sleep_minutes_avg: number | null,
  sleep_quality_avg: number | null = null
): TimeseriesPoint {
  return {
    period_start: date,
    period_end: date,
    entry_count: 1,
    mood_avg: 3,
    energy_avg: 3,
    stress_avg: 3,
    sleep_quality_avg,
    sleep_minutes_avg,
  };
}

describe('sleepZeitversatz', () => {
  it('shifts sleep values forward one day when enabled', () => {
    const points = [
      point('2026-03-01', 400, 4),
      point('2026-03-02', 360, 3),
      point('2026-03-03', 480, 5),
    ];
    const shifted = applySleepZeitversatz(points, true);
    expect(shifted[0].sleep_minutes_avg).toBeNull();
    expect(shifted[1].sleep_minutes_avg).toBe(400);
    expect(shifted[1].sleep_quality_avg).toBe(4);
    expect(shifted[2].sleep_minutes_avg).toBe(360);
    expect(points[1].sleep_minutes_avg).toBe(360); // original unchanged
  });

  it('is a no-op when disabled', () => {
    const points = [point('2026-03-01', 400)];
    expect(applySleepZeitversatz(points, false)[0].sleep_minutes_avg).toBe(400);
  });
});
