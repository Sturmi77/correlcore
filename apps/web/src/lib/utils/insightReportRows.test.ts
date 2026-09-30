import { describe, expect, it } from 'vitest';
import type { InsightResponse } from '$lib/api/insights';
import { buildInsightReportRows, toInsightReportRow } from './insightReportRows';

const insight: InsightResponse = {
  id: 'a',
  user_id: 'u',
  insight_type: 'pointbiserial',
  tier: 'robust',
  metric: 'mood_score',
  subject_type: 'tag',
  subject_id: 'sport',
  subject_label: 'Frühstück, Büro; "lang"',
  effect_size: 0.42,
  confidence: 0.91,
  sample_n: 100,
  statement: 'Association.',
  flags: {},
  payload: {
    tagged_count: 5,
    untagged_count: 95,
    analysis_window_start: '2026-01-01',
    analysis_window_end: '2026-04-10',
  },
  generated_for_date: '2026-04-11',
  generated_at: '2026-04-11T03:00:00Z',
  created_at: '2026-04-11T03:00:00Z',
  updated_at: '2026-04-11T03:00:00Z',
};

describe('InsightReportRow', () => {
  it('keeps evidence, group sizes, total, and actual analysis window together', () => {
    expect(toInsightReportRow(insight)).toMatchObject({
      factor: 'Frühstück, Büro; "lang"',
      effect: 0.42,
      confidence: 0.91,
      sampleWith: 5,
      sampleWithout: 95,
      sampleTotal: 100,
      analysisWindowStart: '2026-01-01',
      analysisWindowEnd: '2026-04-10',
    });
  });

  it('marks unavailable evidence as null instead of inventing values', () => {
    const row = toInsightReportRow({ ...insight, payload: {} });
    expect(row.sampleWith).toBeNull();
    expect(row.sampleWithout).toBeNull();
    expect(row.analysisWindowStart).toBeNull();
    expect(row.analysisWindowEnd).toBeNull();
  });
});

describe('InsightReportRow language', () => {
  const t = (key: string) => (key === 'trends.metric.mood' ? 'Stimmung' : key);

  it('exports the localised metric name in target and relationship', () => {
    const row = toInsightReportRow(insight, t);
    expect(row.target).toBe('Stimmung');
    expect(row.relationship).toBe('Frühstück, Büro; "lang" ↔ Stimmung');
  });

  it('does not pass the array index on as a translator when building rows', () => {
    const [row] = buildInsightReportRows([insight]);
    expect(row.target).toBe('mood_score');
  });
});
