import { describe, expect, it } from 'vitest';
import {
  buildWorkContextHeatmapRows,
  WORK_CONTEXT_METRICS,
  workContextGoodnessLevel,
  workContextMetricAvg,
  workContextMetricGoodness,
} from './homeWorkContextSummary';

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
});
