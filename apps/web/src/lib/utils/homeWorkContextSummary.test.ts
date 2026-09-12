import { describe, expect, it } from 'vitest';
import type { MetricTrend, WorkContextSummaryItem } from '$lib/api/dashboard';
import {
  buildWorkContextHeatmapRows,
  nextWorkContextSort,
  sortWorkContextHeatmapRows,
  workContextHasTrendData,
  workContextHasVisibleTrend,
  WORK_CONTEXT_METRICS,
  WORK_CONTEXT_RELATIVE_MIN_SPAN,
  workContextColumnRange,
  workContextGoodnessLevel,
  workContextMetricAvg,
  workContextMetricGoodness,
} from './homeWorkContextSummary';

const trend = (direction: MetricTrend['direction']): MetricTrend => ({
  // A live `unknown` still carries the current-window mean; only the comparison
  // is withheld. current_avg is kept so the row is not dropped by the builder.
  current_avg: 4,
  previous_avg: direction === 'unknown' ? null : 3,
  current_n: 8,
  previous_n: direction === 'unknown' ? 1 : 8,
  delta: direction === 'unknown' ? null : 1,
  direction,
});

const item = (overrides: Partial<WorkContextSummaryItem> = {}): WorkContextSummaryItem => ({
  work_context: 'office',
  entry_count: 8,
  mood_avg: 3.5,
  energy_avg: 3.5,
  stress_avg: 2.5,
  ...overrides,
});

describe('homeWorkContextSummary trend detection', () => {
  it('reports trend data present only when a MetricTrend object is attached', () => {
    expect(workContextHasTrendData([item()])).toBe(false);
    expect(workContextHasTrendData([item({ mood_trend: trend('unknown') })])).toBe(true);
    expect(workContextHasTrendData([item({ stress_trend: trend('down') })])).toBe(true);
  });

  it('reports a visible trend only when a built cell resolves to a glyph', () => {
    const allUnknown = buildWorkContextHeatmapRows([
      item({
        mood_trend: trend('unknown'),
        energy_trend: trend('unknown'),
        stress_trend: trend('unknown'),
      }),
    ]);
    expect(workContextHasVisibleTrend(allUnknown)).toBe(false);

    const oneVisible = buildWorkContextHeatmapRows([item({ mood_trend: trend('up') })]);
    expect(workContextHasVisibleTrend(oneVisible)).toBe(true);
  });
});

describe('homeWorkContextSummary', () => {
  const items = [
    {
      work_context: 'office' as const,
      entry_count: 8,
      mood_avg: 3.75,
      energy_avg: 3.4,
      stress_avg: 2.8,
    },
    {
      work_context: 'homeoffice' as const,
      entry_count: 5,
      mood_avg: 4.1,
      energy_avg: 3.8,
      stress_avg: 2.1,
    },
    {
      work_context: 'weekend' as const,
      entry_count: 2,
      mood_avg: 2.5,
      energy_avg: 3,
      stress_avg: 3,
    },
  ];

  it('reads raw averages per metric', () => {
    expect(workContextMetricAvg(items[0], 'mood')).toBe(3.75);
    expect(workContextMetricAvg(items[0], 'stress')).toBe(2.8);
    expect(workContextMetricAvg({ ...items[0], mood_avg: null }, 'mood')).toBeNull();
  });

  it('normalises stress to goodness (inverted) and leaves mood/energy untouched', () => {
    expect(workContextMetricGoodness(items[1], 'mood')).toBe(4.1);
    expect(workContextMetricGoodness(items[1], 'energy')).toBe(3.8);
    // stress 2.1 on a 1–5 scale -> goodness 1 + 5 - 2.1 = 3.9
    expect(workContextMetricGoodness(items[1], 'stress')).toBeCloseTo(3.9, 5);
  });

  it('buckets goodness into heatmap levels (0 = no data)', () => {
    expect(workContextGoodnessLevel(null)).toBe(0);
    expect(workContextGoodnessLevel(1)).toBe(1);
    expect(workContextGoodnessLevel(4.1)).toBe(4);
  });

  it('stretches levels across a wide column range (#854 relative scale)', () => {
    const range = { min: 1.8, max: 4.0 };
    expect(range.max - range.min).toBeGreaterThanOrEqual(WORK_CONTEXT_RELATIVE_MIN_SPAN);
    expect(workContextGoodnessLevel(1.8, range)).toBe(1);
    expect(workContextGoodnessLevel(4.0, range)).toBe(4);
    expect(workContextGoodnessLevel(2.9, range)).toBe(2);
  });

  it('falls back to the absolute 1–5 map when the column span is narrow', () => {
    const range = { min: 3.5, max: 3.7 };
    expect(range.max - range.min).toBeLessThan(WORK_CONTEXT_RELATIVE_MIN_SPAN);
    // Absolute: 3.5/5 = 0.7 → level 3; 3.7/5 = 0.74 → level 3
    expect(workContextGoodnessLevel(3.5, range)).toBe(3);
    expect(workContextGoodnessLevel(3.7, range)).toBe(3);
  });

  it('builds one row per context with all three metrics in column order', () => {
    const rows = buildWorkContextHeatmapRows(items);
    expect(rows).toHaveLength(3);
    expect(rows[0].cells.map((cell) => cell.metric)).toEqual([...WORK_CONTEXT_METRICS]);
  });

  it('orders rows best-situation-first by mean goodness', () => {
    const rows = buildWorkContextHeatmapRows(items);
    expect(rows.map((row) => row.work_context)).toEqual(['homeoffice', 'office', 'weekend']);
  });

  it('drops contexts without entries and respects the limit', () => {
    const withEmpty = [
      ...items,
      { work_context: 'sick' as const, entry_count: 0, mood_avg: 5, energy_avg: 5, stress_avg: 1 },
    ];
    expect(buildWorkContextHeatmapRows(withEmpty).map((row) => row.work_context)).not.toContain(
      'sick'
    );
    expect(buildWorkContextHeatmapRows(items, 2)).toHaveLength(2);
  });

  it('inverts stress so lower raw stress yields a stronger cell level', () => {
    const rows = buildWorkContextHeatmapRows(items);
    const homeoffice = rows.find((row) => row.work_context === 'homeoffice')!;
    const weekend = rows.find((row) => row.work_context === 'weekend')!;
    const stressLevel = (row: (typeof rows)[number]) =>
      row.cells.find((cell) => cell.metric === 'stress')!.level;
    // homeoffice stress 2.1 (goodness 3.9) beats weekend stress 3.0 (goodness 3.0)
    expect(stressLevel(homeoffice)).toBeGreaterThan(stressLevel(weekend));
  });

  it('assigns opposite ends of the ramp to wide mood gaps after relative scaling', () => {
    const rows = buildWorkContextHeatmapRows([
      {
        work_context: 'office',
        entry_count: 6,
        mood_avg: 1.8,
        energy_avg: 3,
        stress_avg: 3,
      },
      {
        work_context: 'vacation',
        entry_count: 4,
        mood_avg: 4.0,
        energy_avg: 3,
        stress_avg: 3,
      },
    ]);
    const moodLevel = (context: string) =>
      rows
        .find((row) => row.work_context === context)!
        .cells.find((cell) => cell.metric === 'mood')!.level;
    expect(moodLevel('office')).toBe(1);
    expect(moodLevel('vacation')).toBe(4);
    expect(workContextColumnRange(rows, 'mood')).toEqual({ min: 1.8, max: 4.0 });
  });

  it('prefers window current_avg and exposes a visible trend direction (#868)', () => {
    const rows = buildWorkContextHeatmapRows([
      {
        work_context: 'office',
        entry_count: 8,
        mood_avg: 2.0,
        energy_avg: 3.4,
        stress_avg: 2.8,
        mood_trend: {
          current_avg: 3.9,
          previous_avg: 3.2,
          current_n: 8,
          previous_n: 8,
          delta: 0.7,
          direction: 'up',
        },
        energy_trend: {
          current_avg: 3.4,
          previous_avg: null,
          current_n: 8,
          previous_n: 1,
          delta: null,
          direction: 'unknown',
        },
      },
    ]);
    const mood = rows[0].cells.find((cell) => cell.metric === 'mood')!;
    const energy = rows[0].cells.find((cell) => cell.metric === 'energy')!;
    expect(mood.avg).toBe(3.9);
    expect(mood.trendDirection).toBe('up');
    expect(energy.avg).toBe(3.4);
    expect(energy.trendDirection).toBeNull();
  });

  it('does not show all-time as a 28-day average when the window is empty', () => {
    const rows = buildWorkContextHeatmapRows([
      {
        work_context: 'office',
        entry_count: 8,
        mood_avg: 2.0,
        energy_avg: 3.4,
        stress_avg: 2.8,
        mood_trend: {
          current_avg: null,
          previous_avg: null,
          current_n: 0,
          previous_n: 0,
          delta: null,
          direction: 'unknown',
        },
      },
    ]);
    const mood = rows[0].cells.find((cell) => cell.metric === 'mood')!;
    expect(mood.avg).toBeNull();
    expect(mood.trendDirection).toBeNull();
  });

  describe('nextWorkContextSort', () => {
    it('cycles a column asc → desc → default', () => {
      expect(nextWorkContextSort(null, 'stress')).toEqual({ column: 'stress', direction: 'asc' });
      expect(nextWorkContextSort({ column: 'stress', direction: 'asc' }, 'stress')).toEqual({
        column: 'stress',
        direction: 'desc',
      });
      expect(nextWorkContextSort({ column: 'stress', direction: 'desc' }, 'stress')).toBeNull();
    });

    it('starts a fresh ascending sort when switching columns', () => {
      expect(nextWorkContextSort({ column: 'stress', direction: 'desc' }, 'mood')).toEqual({
        column: 'mood',
        direction: 'asc',
      });
    });
  });

  describe('sortWorkContextHeatmapRows', () => {
    const rows = buildWorkContextHeatmapRows(items);

    it('keeps the default best-first order when sort is null', () => {
      expect(sortWorkContextHeatmapRows(rows, null).map((row) => row.work_context)).toEqual(
        rows.map((row) => row.work_context)
      );
    });

    it('sorts by a metric average in both directions', () => {
      const stressOf = (context: string) =>
        rows
          .find((row) => row.work_context === context)!
          .cells.find((cell) => cell.metric === 'stress')!.avg;
      // stress_avg: office 2.8, homeoffice 2.1, weekend 3.0
      expect(stressOf('office')).toBe(2.8);

      const asc = sortWorkContextHeatmapRows(rows, { column: 'stress', direction: 'asc' });
      expect(asc.map((row) => row.work_context)).toEqual(['homeoffice', 'office', 'weekend']);

      const desc = sortWorkContextHeatmapRows(rows, { column: 'stress', direction: 'desc' });
      expect(desc.map((row) => row.work_context)).toEqual(['weekend', 'office', 'homeoffice']);
    });

    it('sorts by the situation label using the provided resolver', () => {
      const labelFor = (wc: string) =>
        ({ office: 'Büro', homeoffice: 'Homeoffice', weekend: 'Wochenende' })[wc] ?? wc;
      const asc = sortWorkContextHeatmapRows(
        rows,
        { column: 'work_context', direction: 'asc' },
        labelFor
      );
      expect(asc.map((row) => row.work_context)).toEqual(['office', 'homeoffice', 'weekend']);

      const desc = sortWorkContextHeatmapRows(
        rows,
        { column: 'work_context', direction: 'desc' },
        labelFor
      );
      expect(desc.map((row) => row.work_context)).toEqual(['weekend', 'homeoffice', 'office']);
    });

    it('always sorts rows without a value to the end', () => {
      const withGap = buildWorkContextHeatmapRows([
        ...items,
        {
          work_context: 'sick' as const,
          entry_count: 3,
          mood_avg: 3,
          energy_avg: 3,
          stress_avg: null,
        },
      ]);
      const asc = sortWorkContextHeatmapRows(withGap, { column: 'stress', direction: 'asc' });
      const desc = sortWorkContextHeatmapRows(withGap, { column: 'stress', direction: 'desc' });
      expect(asc[asc.length - 1].work_context).toBe('sick');
      expect(desc[desc.length - 1].work_context).toBe('sick');
    });

    it('does not mutate the input rows', () => {
      const before = rows.map((row) => row.work_context);
      sortWorkContextHeatmapRows(rows, { column: 'stress', direction: 'desc' });
      expect(rows.map((row) => row.work_context)).toEqual(before);
    });
  });
});
