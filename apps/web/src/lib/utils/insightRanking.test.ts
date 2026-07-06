import { describe, expect, it } from 'vitest';
import type { InsightResponse } from '$lib/api/insights';
import { insightPriorityScore, rankInsights } from './insightRanking';

function makeInsight(overrides: Partial<InsightResponse>): InsightResponse {
  return {
    id: 'insight',
    user_id: 'user',
    insight_type: 'spearman',
    tier: 'developing',
    metric: 'mood',
    subject_type: 'metric',
    subject_id: 'energy',
    subject_label: 'Energy',
    effect_size: 0.4,
    confidence: 0.5,
    sample_n: 30,
    statement: 'A descriptive association.',
    flags: { causal_claim: false },
    payload: {},
    generated_for_date: '2026-06-20',
    generated_at: '2026-06-20T10:00:00Z',
    created_at: '2026-06-20T10:00:00Z',
    updated_at: '2026-06-20T10:00:00Z',
    ...overrides,
  };
}

describe('insight ranking', () => {
  it('scores confidence and absolute effect size', () => {
    expect(insightPriorityScore(makeInsight({ confidence: 0.75, effect_size: -0.4 }))).toBeCloseTo(
      0.3
    );
  });

  it('ranks the strongest signal without mutating the API response', () => {
    const low = makeInsight({ id: 'low', confidence: 0.4, effect_size: 0.2 });
    const high = makeInsight({ id: 'high', confidence: 0.8, effect_size: -0.6 });
    const input = [low, high];

    expect(rankInsights(input).map((insight) => insight.id)).toEqual(['high', 'low']);
    expect(input.map((insight) => insight.id)).toEqual(['low', 'high']);
  });

  it('ranks non-confounded insights ahead of confounded ties', () => {
    const confounded = makeInsight({
      id: 'conf',
      payload: { confounder: 'weekday' },
    });
    const clean = makeInsight({ id: 'clean' });

    expect(rankInsights([confounded, clean]).map((insight) => insight.id)).toEqual([
      'clean',
      'conf',
    ]);
  });

  it('downgrades work-context confounded ties too', () => {
    const confounded = makeInsight({
      id: 'conf',
      flags: { work_context_confounded: true },
    });
    const clean = makeInsight({ id: 'clean' });

    expect(rankInsights([confounded, clean]).map((insight) => insight.id)).toEqual([
      'clean',
      'conf',
    ]);
  });

  it('uses generation time and id as deterministic tie breakers', () => {
    const older = makeInsight({ id: 'older', generated_at: '2026-06-19T10:00:00Z' });
    const newerB = makeInsight({ id: 'b', generated_at: '2026-06-20T10:00:00Z' });
    const newerA = makeInsight({ id: 'a', generated_at: '2026-06-20T10:00:00Z' });

    expect(rankInsights([older, newerB, newerA]).map((insight) => insight.id)).toEqual([
      'a',
      'b',
      'older',
    ]);
  });
});
