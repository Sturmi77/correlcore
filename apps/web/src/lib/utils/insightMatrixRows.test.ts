import { describe, expect, it } from 'vitest';
import type { InsightResponse } from '$lib/api/insights';
import { buildMatrixDisplayRows, matrixCoverageStats, matrixRowKey } from './insightMatrixRows';

const base: InsightResponse = {
  id: 'insight-1',
  user_id: 'user-1',
  insight_type: 'pointbiserial',
  tier: 'developing',
  metric: 'mood_score',
  subject_type: 'tag',
  subject_id: 'plain-tag',
  subject_label: 'Sport',
  effect_size: 0.4,
  confidence: 0.7,
  sample_n: 24,
  statement: 'Sport lines up with higher mood.',
  flags: {},
  payload: {},
  generated_for_date: '2026-05-12',
  generated_at: '2026-05-12T03:00:00Z',
  created_at: '2026-05-12T03:00:00Z',
  updated_at: '2026-05-12T03:00:00Z',
};

describe('buildMatrixDisplayRows', () => {
  it('splits strong and weak bands after dedupe', () => {
    const result = buildMatrixDisplayRows([
      { ...base, id: 'weak', subject_label: 'Weak', confidence: 0.15 },
      { ...base, id: 'strong', subject_label: 'Strong', effect_size: -0.7 },
      { ...base, id: 'noise', subject_label: 'Noise', confidence: 0.05 },
    ]);
    expect(result.strong.map((row) => row.subject_label)).toEqual(['Strong']);
    expect(result.weak.map((row) => row.subject_label)).toEqual(['Weak']);
  });

  it('dedupes tag slug variants into one key', () => {
    expect(
      matrixRowKey({
        ...base,
        subject_id: 'a',
        payload: { tag_slug: 'Alcohol' },
      })
    ).toBe(
      matrixRowKey({
        ...base,
        subject_id: 'b',
        payload: { tag_slug: 'alcohol' },
      })
    );
  });
});

describe('matrixCoverageStats', () => {
  it('reports row count and max sample_n', () => {
    expect(
      matrixCoverageStats([
        { ...base, sample_n: 10 },
        { ...base, id: '2', sample_n: 40 },
      ])
    ).toEqual({ rowCount: 2, maxSampleN: 40 });
  });
});
