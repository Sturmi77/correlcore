import { describe, expect, it } from 'vitest';
import type { InsightResponse } from '$lib/api/insights';
import { filterInsightsByTab } from './insightFeedFilter';

function makeInsight(overrides: Partial<InsightResponse> = {}): InsightResponse {
  return {
    id: 'i1',
    user_id: 'u1',
    insight_type: 'spearman',
    tier: 'developing',
    metric: 'mood',
    subject_type: 'tag',
    subject_id: 'sport',
    subject_label: 'sport',
    confidence: 0.5,
    effect_size: 0.3,
    sample_n: 30,
    statement: 'Test',
    flags: {},
    payload: {},
    generated_for_date: '2026-05-10',
    generated_at: '2026-05-10T10:00:00Z',
    created_at: '2026-05-10T10:00:00Z',
    updated_at: '2026-05-10T10:00:00Z',
    ...overrides,
  };
}

describe('insightFeedFilter', () => {
  it('filters mood insights only', () => {
    const mood = makeInsight({ id: 'm', metric: 'mood' });
    const sleep = makeInsight({ id: 's', metric: 'sleep' });
    expect(filterInsightsByTab([mood, sleep], 'mood')).toEqual([mood]);
  });

  it('includes symptom association insights in symptoms tab', () => {
    const symptom = makeInsight({
      metric: 'mood',
      insight_type: 'symptom_mood_association',
      subject_type: 'symptom',
    });
    const tag = makeInsight({ metric: 'mood', subject_type: 'tag' });
    expect(filterInsightsByTab([symptom, tag], 'symptoms')).toEqual([symptom]);
  });

  it('filters calendar and work context insights in context tab', () => {
    const weekday = makeInsight({ id: 'weekday', insight_type: 'weekday_pattern' });
    const workContext = makeInsight({
      id: 'work',
      insight_type: 'work_context_pattern',
      payload: { work_context: 'office' },
    });
    const mood = makeInsight({ id: 'mood', insight_type: 'spearman', metric: 'mood' });

    expect(filterInsightsByTab([weekday, workContext, mood], 'context')).toEqual([
      weekday,
      workContext,
    ]);
  });
});
