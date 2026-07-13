import { describe, expect, it } from 'vitest';
import {
  buildWorkContextDisplayItems,
  weightedMoodAverage,
  weightedMetricAverage,
  workContextMetricBarWidth,
  workContextMetricHighLow,
  workContextMoodBarWidth,
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

  it('computes weighted mood average across contexts', () => {
    expect(weightedMoodAverage(items)).toBeCloseTo(3.7, 1);
    expect(weightedMetricAverage(items, 'energy')).toBeCloseTo(3.5, 1);
  });

  it('sorts by mood deviation and encodes mood in bar width', () => {
    const display = buildWorkContextDisplayItems(items, 'mood');
    expect(display[0].work_context).toBe('weekend');
    expect(display[1].work_context).toBe('homeoffice');
    expect(workContextMoodBarWidth(display[0].metricAvg)).toBe('50%');
    expect(workContextMetricBarWidth('mood', display[1].metricAvg)).toBe('82%');
  });

  it('uses energy averages when energy metric is selected', () => {
    const display = buildWorkContextDisplayItems(items, 'energy');
    expect(display.every((item) => item.metricAvg !== null)).toBe(true);
    expect(workContextMetricBarWidth('energy', display[0].metricAvg)).toBe('60%');
  });

  it('marks the lowest stress value as high (best) when inverted', () => {
    const stressValues = items.map((item) => item.stress_avg!);
    expect(workContextMetricHighLow(stressValues, 'stress')).toEqual({ high: 2.1, low: 3 });
  });
});
