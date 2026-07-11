import { describe, expect, it } from 'vitest';
import {
  buildWorkContextDisplayItems,
  weightedMoodAverage,
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
  });

  it('sorts by mood deviation and encodes mood in bar width', () => {
    const display = buildWorkContextDisplayItems(items);
    expect(display[0].work_context).toBe('weekend');
    expect(display[1].work_context).toBe('homeoffice');
    expect(workContextMoodBarWidth(display[0].mood_avg)).toBe('50%');
    expect(workContextMoodBarWidth(display[1].mood_avg)).toBe('82%');
  });
});
