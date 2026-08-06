import { describe, expect, it } from 'vitest';
import {
  buildBucketAxisLinePoints,
  buildDailyAxisLinePoints,
  buildIsoDateRange,
  buildLinePoints,
  dailyAxisChartWidth,
  dailyAxisXForDate,
  dailyPlotContentWidth,
  formatTimeseriesTick,
  heatmapLevel,
  linePath,
  metricStyles,
  smoothTimeseriesPoints,
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
          sleep_quality_avg: null,
        },
        {
          period_start: '2026-05-02',
          period_end: '2026-05-02',
          entry_count: 1,
          mood_avg: 5,
          energy_avg: null,
          stress_avg: null,
          sleep_quality_avg: null,
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

  it('builds a shared daily axis for aligned chart and heatmap rows', () => {
    const dates = buildIsoDateRange('2026-05-01', '2026-05-03');
    const layout = { labelWidth: 120, dayWidth: 10, dayGap: 2, rightPadding: 8 };

    expect(dates).toEqual(['2026-05-01', '2026-05-02', '2026-05-03']);
    expect(dailyAxisXForDate('2026-05-02', dates, layout)).toBe(139);
    expect(dailyAxisChartWidth(dates, layout)).toBe(164);
  });

  it('includes leading dayGap in plot content width (#629)', () => {
    const dates = buildIsoDateRange('2026-05-01', '2026-05-03');
    const layout = { labelWidth: 0, dayWidth: 10, dayGap: 2, rightPadding: 0 };
    // 2 + (3*10 + 2*2) + 0 = 36 — matches last cell right edge with leading gap.
    expect(dailyPlotContentWidth(dates, layout)).toBe(36);
  });

  it('maps timeseries points onto zoom buckets by mean of days with values', () => {
    const layout = { labelWidth: 120, dayWidth: 10, dayGap: 2, rightPadding: 8 };
    const points = buildBucketAxisLinePoints(
      [
        {
          period_start: '2026-05-01',
          period_end: '2026-05-01',
          entry_count: 1,
          mood_avg: 2,
          energy_avg: null,
          stress_avg: null,
          sleep_quality_avg: null,
        },
        {
          period_start: '2026-05-02',
          period_end: '2026-05-02',
          entry_count: 0,
          mood_avg: null,
          energy_avg: null,
          stress_avg: null,
          sleep_quality_avg: null,
        },
        {
          period_start: '2026-05-03',
          period_end: '2026-05-03',
          entry_count: 1,
          mood_avg: 4,
          energy_avg: null,
          stress_avg: null,
          sleep_quality_avg: null,
        },
      ],
      'mood_avg',
      [
        {
          id: '2026-05-01_2026-05-03',
          start: '2026-05-01',
          end: '2026-05-03',
          dayCount: 3,
          presentDays: 3,
          partial: false,
          dates: ['2026-05-01', '2026-05-02', '2026-05-03'],
        },
      ],
      40,
      layout
    );

    expect(points).toEqual([{ x: 127, y: 20, value: 3, label: '2026-05-01' }]);
  });

  it('maps timeseries points onto the shared daily axis by date', () => {
    const dates = buildIsoDateRange('2026-05-01', '2026-05-03');
    const layout = { labelWidth: 120, dayWidth: 10, dayGap: 2, rightPadding: 8 };
    const points = buildDailyAxisLinePoints(
      [
        {
          period_start: '2026-05-01',
          period_end: '2026-05-01',
          entry_count: 1,
          mood_avg: 1,
          energy_avg: null,
          stress_avg: null,
          sleep_quality_avg: null,
        },
        {
          period_start: '2026-05-03',
          period_end: '2026-05-03',
          entry_count: 1,
          mood_avg: 5,
          energy_avg: null,
          stress_avg: null,
          sleep_quality_avg: null,
        },
      ],
      'mood_avg',
      dates,
      40,
      layout
    );

    expect(points).toEqual([
      { x: 127, y: 40, value: 1, label: '2026-05-01' },
      { x: 151, y: 0, value: 5, label: '2026-05-03' },
    ]);
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
          sleep_quality_avg: null,
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
          sleep_quality_avg: null,
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
    expect(metricStyles.sleep_quality_avg.shape).toBe('square');
    // Distinct shapes and dasharrays keep the four lines separable without colour.
    expect(new Set(Object.values(metricStyles).map((style) => style.shape)).size).toBe(4);
    expect(new Set(Object.values(metricStyles).map((style) => style.dasharray)).size).toBe(4);
  });

  it('smooths timeseries with a trailing average and preserves null gaps', () => {
    const points = [
      {
        period_start: '2026-05-01',
        period_end: '2026-05-01',
        entry_count: 1,
        mood_avg: 1,
        energy_avg: null,
        stress_avg: 5,
        sleep_quality_avg: null,
      },
      {
        period_start: '2026-05-02',
        period_end: '2026-05-02',
        entry_count: 1,
        mood_avg: 3,
        energy_avg: 4,
        stress_avg: null,
        sleep_quality_avg: null,
      },
      {
        period_start: '2026-05-03',
        period_end: '2026-05-03',
        entry_count: 1,
        mood_avg: 5,
        energy_avg: 2,
        stress_avg: 1,
        sleep_quality_avg: null,
      },
    ];

    const smoothed = smoothTimeseriesPoints(points, 2);

    expect(smoothed.map((point) => point.mood_avg)).toEqual([1, 2, 4]);
    expect(smoothed.map((point) => point.energy_avg)).toEqual([null, 4, 3]);
    // Null on the current day stays null — no carry-forward into calendar gaps.
    expect(smoothed.map((point) => point.stress_avg)).toEqual([5, null, 1]);
  });

  it('does not invent smoothed values on days without metric data', () => {
    const points = [
      {
        period_start: '2026-05-01',
        period_end: '2026-05-01',
        entry_count: 1,
        mood_avg: 4,
        energy_avg: 3,
        stress_avg: 2,
        sleep_quality_avg: null,
      },
      {
        period_start: '2026-05-02',
        period_end: '2026-05-02',
        entry_count: 0,
        mood_avg: null,
        energy_avg: null,
        stress_avg: null,
        sleep_quality_avg: null,
      },
      {
        period_start: '2026-05-03',
        period_end: '2026-05-03',
        entry_count: 0,
        mood_avg: null,
        energy_avg: null,
        stress_avg: null,
        sleep_quality_avg: null,
      },
    ];

    const smoothed = smoothTimeseriesPoints(points, 3);
    expect(smoothed.map((point) => point.mood_avg)).toEqual([4, null, null]);
    expect(smoothed.map((point) => point.entry_count)).toEqual([1, 0, 0]);
  });
});
