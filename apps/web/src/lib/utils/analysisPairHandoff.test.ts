import { describe, expect, it } from 'vitest';
import type { InsightResponse } from '$lib/api/insights';
import {
  analysisPairQuery,
  createAnalysisPair,
  insightMatchesAnalysisPair,
  parseAnalysisPair,
} from './analysisPairHandoff';

function insight(overrides: Partial<InsightResponse>): InsightResponse {
  return {
    id: 'insight-1',
    user_id: 'user-1',
    insight_type: 'pointbiserial',
    tier: 'developing',
    metric: 'mood_score',
    subject_type: 'tag',
    subject_id: 'tag-a',
    subject_label: 'A',
    effect_size: 0.4,
    confidence: 0.7,
    sample_n: 30,
    statement: 'test',
    flags: {},
    payload: {},
    generated_for_date: '2026-09-22',
    generated_at: '2026-09-22T03:00:00Z',
    created_at: '2026-09-22T03:00:00Z',
    updated_at: '2026-09-22T03:00:00Z',
    ...overrides,
  };
}

describe('analysis pair handoff', () => {
  const pair = createAnalysisPair(
    { kind: 'symptom', id: 'symptom-a', label: 'Headache' },
    { kind: 'tag', id: 'tag-b', label: 'Meetings' }
  );

  it('round-trips a structured pair in either pin order', () => {
    expect(parseAnalysisPair(new URLSearchParams(analysisPairQuery(pair)))).toEqual(pair);
    const reversed = createAnalysisPair(pair.signals[1], pair.signals[0]);
    expect(
      insightMatchesAnalysisPair(
        insight({
          insight_type: 'symptom_tag_cooccurrence',
          subject_type: 'symptom_tag',
          subject_id: null,
          metric: 'symptom_tag_cooccurrence',
          payload: {
            kind: 'symptom_tag_cooccurrence',
            symptom_id: 'symptom-a',
            tag_id: 'tag-b',
          },
        }),
        reversed
      )
    ).toBe(true);
  });

  it('does not accept a valid single-pin hit as evidence for the pair', () => {
    expect(insightMatchesAnalysisPair(insight({}), pair)).toBe(false);
  });

  it('matches composite and lag identities without relying on subject_id', () => {
    const lagPair = createAnalysisPair(
      { kind: 'tag', id: 'walk', lagDays: 1 },
      { kind: 'metric', id: 'mood_score', metric: 'mood_score', lagDays: 1 }
    );
    expect(
      insightMatchesAnalysisPair(
        insight({
          insight_type: 'symptom_cluster',
          subject_type: 'metric',
          subject_id: null,
          payload: {
            method: 'lag',
            lag_days: 1,
            feature: { kind: 'tag', key: 'tag:walk' },
            target: { kind: 'metric', key: 'mood_score' },
          },
        }),
        lagPair
      )
    ).toBe(true);
  });

  it('keeps work-context identity distinct from a tag with the same id', () => {
    const contextPair = createAnalysisPair(
      { kind: 'work_context', id: 'office', context: 'office' },
      { kind: 'metric', id: 'mood_score', metric: 'mood_score' }
    );
    const contextInsight = insight({
      insight_type: 'work_context_pattern',
      subject_type: 'work_context',
      subject_id: null,
      payload: { work_context: 'office' },
    });
    expect(insightMatchesAnalysisPair(contextInsight, contextPair)).toBe(true);
  });
});
