import { describe, expect, it, vi } from 'vitest';
import type { EntryResponse } from '$lib/api/entries';
import type { InsightResponse } from '$lib/api/insights';
import {
  buildExploreEventWindows,
  datesToEventWindows,
  devEventWindowsFromHeatmaps,
  insightMetricToChartKey,
  isExploreEventsSubject,
  lagFeatureKind,
} from './exploreEventWindows';

const baseInsight = (overrides: Partial<InsightResponse>): InsightResponse => ({
  id: 'i1',
  user_id: 'u1',
  insight_type: 'pointbiserial',
  tier: 'preliminary',
  metric: 'mood',
  subject_type: 'tag',
  subject_id: 'tag-a',
  subject_label: 'Focus',
  effect_size: 0.3,
  confidence: 0.5,
  sample_n: 10,
  statement: null,
  flags: {},
  payload: {},
  generated_for_date: '2026-07-01',
  generated_at: '2026-07-01T00:00:00Z',
  created_at: '2026-07-01T00:00:00Z',
  updated_at: '2026-07-01T00:00:00Z',
  ...overrides,
});

const entry = (id: string, entry_date: string): EntryResponse => ({
  id,
  user_id: 'u1',
  entry_date,
  slot: 'day',
  mood_score: 3,
  energy: 3,
  stress: 2,
  cycle_day: null,
  source: 'direct',
  work_context: 'office',
  note: null,
  created_at: `${entry_date}T08:00:00Z`,
  updated_at: `${entry_date}T08:00:00Z`,
});

describe('exploreEventWindows', () => {
  it('detects tag and symptom subjects only', () => {
    expect(isExploreEventsSubject(baseInsight({ subject_type: 'tag' }))).toBe(true);
    expect(isExploreEventsSubject(baseInsight({ subject_type: 'symptom' }))).toBe(true);
    expect(isExploreEventsSubject(baseInsight({ subject_type: 'metric' }))).toBe(false);
    expect(isExploreEventsSubject(baseInsight({ subject_type: 'weekday' }))).toBe(false);
  });

  it('enables explore-events for lag insights with a tag/symptom feature (#488)', () => {
    // Outcome (subject) is a metric, so subject_type alone would hide the sheet.
    const lagInsight = baseInsight({
      subject_type: 'metric',
      payload: { method: 'lag', lag_days: 2, feature: { kind: 'tag', slug: 'cycling' } },
    });
    expect(lagFeatureKind(lagInsight)).toBe('tag');
    expect(isExploreEventsSubject(lagInsight)).toBe(true);

    // A lag insight whose feature is a metric has no presence dates → not eligible.
    const metricFeatureLag = baseInsight({
      subject_type: 'metric',
      payload: { method: 'lag', lag_days: 2, feature: { kind: 'metric', slug: 'mood' } },
    });
    expect(lagFeatureKind(metricFeatureLag)).toBeNull();
    expect(isExploreEventsSubject(metricFeatureLag)).toBe(false);
  });

  it('maps insight metrics to chart keys', () => {
    expect(insightMetricToChartKey('mood')).toBe('mood_avg');
    expect(insightMetricToChartKey('energy_avg')).toBe('energy_avg');
    expect(insightMetricToChartKey('stress')).toBe('stress_avg');
  });

  it('deduplicates and sorts onset dates', () => {
    expect(datesToEventWindows(['2026-07-03', '2026-07-01', '2026-07-03'], 'Focus')).toEqual([
      { onset: '2026-07-01', label: 'Focus' },
      { onset: '2026-07-03', label: 'Focus' },
    ]);
  });

  it('builds tag presence windows from entries', async () => {
    const listTagsForEntry = vi.fn(async (entryId: string) =>
      entryId === 'e1' ? [{ id: 'tag-a' }] : [{ id: 'tag-b' }]
    );
    const listSymptomsForEntry = vi.fn(async () => []);

    const windows = await buildExploreEventWindows(
      baseInsight({ subject_type: 'tag', subject_id: 'tag-a' }),
      [entry('e1', '2026-07-01'), entry('e2', '2026-07-02')],
      listTagsForEntry,
      listSymptomsForEntry
    );

    expect(windows).toEqual([{ onset: '2026-07-01', label: 'Focus' }]);
  });

  it('returns empty windows for unsupported subjects', async () => {
    const windows = await buildExploreEventWindows(
      baseInsight({ subject_type: 'metric', subject_id: 'energy' }),
      [entry('e1', '2026-07-01')],
      vi.fn(async () => []),
      vi.fn(async () => [])
    );

    expect(windows).toEqual([]);
  });

  it('derives dev windows from heatmaps', () => {
    const insight = baseInsight({ subject_type: 'tag', subject_id: 't1', subject_label: 'Walk' });
    const windows = devEventWindowsFromHeatmaps(
      insight,
      {
        start_date: '2026-06-01',
        end_date: '2026-07-01',
        tags: [
          {
            tag_id: 't1',
            slug: 'walk',
            name: 'Walk',
            category: 'sport',
            color: null,
            days: [
              { date: '2026-06-10', count: 1 },
              { date: '2026-06-12', count: 0 },
            ],
          },
        ],
      },
      { start_date: '2026-06-01', end_date: '2026-07-01', symptoms: [] }
    );

    expect(windows).toEqual([{ onset: '2026-06-10', label: 'Walk' }]);
  });
});
