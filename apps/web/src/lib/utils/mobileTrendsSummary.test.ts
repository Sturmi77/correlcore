import { describe, expect, it } from 'vitest';
import type { SymptomHeatmapResponse, TagHeatmapResponse, TimeseriesPoint } from '$lib/api/stats';
import { buildMobileTrendsSummary } from './mobileTrendsSummary';

const points: TimeseriesPoint[] = [
  {
    period_start: '2026-06-02',
    period_end: '2026-06-02',
    entry_count: 2,
    mood_avg: 4,
    energy_avg: 3,
    stress_avg: 2,
  },
  {
    period_start: '2026-06-01',
    period_end: '2026-06-01',
    entry_count: 1,
    mood_avg: 3,
    energy_avg: 4,
    stress_avg: 4,
  },
];

const tags: TagHeatmapResponse = {
  start_date: '2026-06-01',
  end_date: '2026-06-02',
  tags: [
    {
      tag_id: 'walk',
      slug: 'walk',
      name: 'Walk',
      category: 'sport',
      color: null,
      days: [{ date: '2026-06-01', count: 1 }],
    },
    {
      tag_id: 'focus',
      slug: 'focus',
      name: 'Focus',
      category: 'work',
      color: null,
      days: [
        { date: '2026-06-01', count: 2 },
        { date: '2026-06-02', count: 1 },
      ],
    },
  ],
};

const symptoms: SymptomHeatmapResponse = {
  start_date: '2026-06-01',
  end_date: '2026-06-02',
  symptoms: [
    {
      symptom_id: 'headache',
      slug: 'headache',
      name: 'Headache',
      icon: null,
      days: [{ date: '2026-06-01', count: 2, max_intensity: 2 }],
    },
    {
      symptom_id: 'fatigue',
      slug: 'fatigue',
      name: 'Fatigue',
      icon: null,
      days: [{ date: '2026-06-02', count: 2, max_intensity: 3 }],
    },
  ],
};

describe('buildMobileTrendsSummary', () => {
  it('summarises existing analytics without changing their domain values', () => {
    expect(buildMobileTrendsSummary(points, tags, symptoms)).toEqual({
      entryCount: 3,
      movement: { metric: 'stress_avg', from: 4, to: 2, delta: -2 },
      tag: { id: 'focus', name: 'Focus', occurrences: 3, activeDays: 2 },
      symptom: { id: 'fatigue', name: 'Fatigue', reports: 2, peakIntensity: 3 },
    });
  });

  it('returns explicit empty signals when the source responses contain no usable data', () => {
    expect(buildMobileTrendsSummary([], null, null)).toEqual({
      entryCount: 0,
      movement: null,
      tag: null,
      symptom: null,
    });
  });
});
