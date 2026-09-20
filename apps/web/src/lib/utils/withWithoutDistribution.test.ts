import { describe, expect, it } from 'vitest';
import type { InsightResponse } from '$lib/api/insights';
import {
  isNullAssociation,
  isWithWithoutInsight,
  parseWithWithoutView,
} from './withWithoutDistribution';

function baseInsight(overrides: Partial<InsightResponse> = {}): InsightResponse {
  return {
    id: 'i1',
    user_id: 'u1',
    insight_type: 'pointbiserial',
    tier: 'developing',
    metric: 'mood_score',
    subject_type: 'tag',
    subject_id: 't1',
    subject_label: 'Sport',
    effect_size: 0.42,
    confidence: 0.6,
    sample_n: 40,
    statement: 'Sport days look higher.',
    flags: {},
    payload: {
      tagged_count: 16,
      untagged_count: 24,
      tagged_mood_avg: 4.1,
      untagged_mood_avg: 3.2,
      with_distribution: [1, 2, 3, 6, 4],
      without_distribution: [4, 6, 8, 4, 2],
      with_good_count: 10,
      without_good_count: 6,
      good_threshold: 4,
      scale_min: 1,
      scale_max: 5,
      outcome: 'association',
    },
    generated_for_date: '2026-09-01',
    generated_at: '2026-09-01T00:00:00Z',
    created_at: '2026-09-01T00:00:00Z',
    updated_at: '2026-09-01T00:00:00Z',
    ...overrides,
  };
}

describe('withWithoutDistribution', () => {
  it('parses two-denominator frequencies and distributions', () => {
    const view = parseWithWithoutView(baseInsight());
    expect(view).not.toBeNull();
    expect(view?.withN).toBe(16);
    expect(view?.withoutN).toBe(24);
    expect(view?.withGood).toBe(10);
    expect(view?.withoutGood).toBe(6);
    expect(view?.withDistribution).toEqual([1, 2, 3, 6, 4]);
    expect(view?.meanShift).toBe(0.9);
    expect(view?.overlap).toBe('low');
    expect(isWithWithoutInsight(baseInsight())).toBe(true);
  });

  it('marks null_association as a non-result with high overlap', () => {
    const insight = baseInsight({
      insight_type: 'null_association',
      effect_size: 0.05,
      payload: {
        ...baseInsight().payload,
        outcome: 'null',
      },
      flags: { non_result: true },
    });
    expect(isNullAssociation(insight)).toBe(true);
    expect(parseWithWithoutView(insight)?.isNullResult).toBe(true);
    expect(parseWithWithoutView(insight)?.overlap).toBe('high');
  });

  it('returns null when group sizes are missing', () => {
    expect(
      parseWithWithoutView(
        baseInsight({
          payload: { tagged_mood_avg: 4 },
        })
      )
    ).toBeNull();
  });
});
