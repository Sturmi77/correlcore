import { describe, expect, it } from 'vitest';
import type { InsightResponse, InsightVerificationResponse } from '$lib/api/insights';
import { hasUsableVerification, supportsInsightVerification } from './insightVerification';

const insight: InsightResponse = {
  id: 'i',
  user_id: 'u',
  insight_type: 'pointbiserial',
  tier: 'robust',
  metric: 'mood_score',
  subject_type: 'tag',
  subject_id: 't',
  subject_label: 'Sport',
  effect_size: 0.4,
  confidence: 0.8,
  sample_n: 30,
  statement: null,
  flags: {},
  payload: {},
  generated_for_date: '2026-09-22',
  generated_at: '2026-09-22T00:00:00Z',
  created_at: '2026-09-22T00:00:00Z',
  updated_at: '2026-09-22T00:00:00Z',
};
const verification: InsightVerificationResponse = {
  range: '90d',
  start_date: '2026-06-01',
  end_date: '2026-09-01',
  metric: 'mood_score',
  subject_label: 'Sport',
  points: [{ date: '2026-06-01', value: 3, present: true }],
  with_mean: 3,
  without_mean: 4,
  with_se: null,
  without_se: null,
  with_n: 1,
  without_n: 2,
};

describe('scatter eligibility', () => {
  it('rejects composite, unsupported metrics and lagged targets', () => {
    expect(supportsInsightVerification(insight)).toBe(true);
    expect(supportsInsightVerification({ ...insight, subject_type: 'composite' })).toBe(false);
    expect(supportsInsightVerification({ ...insight, metric: 'belastung_composite' })).toBe(false);
    expect(
      supportsInsightVerification({ ...insight, payload: { method: 'lag', lag_days: 2 } })
    ).toBe(false);
  });

  it('requires both groups and actual points before offering a scatter control', () => {
    expect(hasUsableVerification(verification)).toBe(true);
    expect(hasUsableVerification({ ...verification, without_n: 0, without_mean: null })).toBe(
      false
    );
    expect(hasUsableVerification({ ...verification, points: [] })).toBe(false);
    expect(hasUsableVerification(null)).toBe(false);
  });
});
