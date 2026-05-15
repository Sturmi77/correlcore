import { describe, expect, it } from 'vitest';
import {
  buildLinePoints,
  formatTimeseriesTick,
  heatmapLevel,
  linePath,
  metricStyles,
} from './charts';

describe('chart utilities', () => {
  it('builds SVG line points and skips nulls', () => {
    const points = buildLinePoints(
      [
        {
          period_start: '2026-05-01',
          period_end: '2026-05-01',
          entry_count: 1,
          mood_avg: 1,
          energy_avg: null,
          stress_avg: null,
        },
        {
          period_start: '2026-05-02',
          period_end: '2026-05-02',
          entry_count: 1,
          mood_avg: 5,
          energy_avg: null,
          stress_avg: null,
        },
      ],
      'mood_avg',
      100,
      40
    );

    expect(points).toEqual([
      { x: 0, y: 40, value: 1, label: '2026-05-01' },
      { x: 100, y: 0, value: 5, label: '2026-05-02' },
    ]);
    expect(linePath(points)).toBe('M 0.00 40.00 L 100.00 0.00');
  });

  it('inverts stress_avg on the chart Y axis (higher raw stress plots lower)', () => {
    const stressed = buildLinePoints(
      [
        {
          period_start: '2026-05-01',
          period_end: '2026-05-01',
          entry_count: 1,
          mood_avg: null,
          energy_avg: null,
          stress_avg: 5,
        },
      ],
      'stress_avg',
      100,
      40
    );
    const relaxed = buildLinePoints(
      [
        {
          period_start: '2026-05-01',
          period_end: '2026-05-01',
          entry_count: 1,
          mood_avg: null,
          energy_avg: null,
          stress_avg: 1,
        },
      ],
      'stress_avg',
      100,
      40
    );
    expect(stressed[0]?.y).toBeGreaterThan(relaxed[0]?.y ?? 0);
  });

  it('maps heatmap counts into five visual levels', () => {
    expect(heatmapLevel(0, 10)).toBe(0);
    expect(heatmapLevel(1, 10)).toBe(1);
    expect(heatmapLevel(5, 10)).toBe(2);
    expect(heatmapLevel(8, 10)).toBe(4);
  });

  it('formats x-axis ticks for the selected timeseries range', () => {
    expect(formatTimeseriesTick('week', '2026-05-09')).toBe('05-09');
    expect(formatTimeseriesTick('month', '2026-05-09')).toBe('05-09');
    expect(formatTimeseriesTick('year', '2026-05-09')).toBe('2026-05');
    expect(formatTimeseriesTick('week', 'bad-date')).toBe('bad-date');
  });

  it('uses non-color metric styles for a11y', () => {
    expect(metricStyles.mood_avg.shape).toBe('circle');
    expect(metricStyles.energy_avg.shape).toBe('diamond');
    expect(metricStyles.stress_avg.shape).toBe('triangle');
    expect(new Set(Object.values(metricStyles).map((style) => style.dasharray)).size).toBe(3);
  });
});
