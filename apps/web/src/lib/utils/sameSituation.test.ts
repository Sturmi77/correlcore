import { describe, expect, it } from 'vitest';
import type { InsightResponse } from '$lib/api/insights';
import { parseSameSituationView } from './sameSituation';

function baseInsight(payload: Record<string, unknown> = {}): InsightResponse {
  return {
    id: 'i1',
    user_id: 'u1',
    insight_type: 'pointbiserial',
    tier: 'developing',
    metric: 'mood_score',
    subject_type: 'tag',
    subject_id: 't1',
    subject_label: 'Sport',
    effect_size: 0.4,
    confidence: 0.6,
    sample_n: 40,
    statement: 'Days tagged Sport currently line up with higher mood scores in your data.',
    flags: {},
    payload: {
      same_work_context: 'homeoffice',
      same_work_context_with_n: 12,
      same_work_context_without_n: 18,
      same_work_context_with_good: 8,
      same_work_context_without_good: 6,
      situation_effect_survives: true,
      weekday_held_coefficient: 0.31,
      calendar_held_coefficient: 0.22,
      ...payload,
    },
    generated_for_date: '2026-05-01',
    generated_at: '2026-05-01T00:00:00Z',
    created_at: '2026-05-01T00:00:00Z',
    updated_at: '2026-05-01T00:00:00Z',
  };
}

describe('parseSameSituationView', () => {
  it('parses same-work-context frequencies for Layer 2 disclosure', () => {
    const view = parseSameSituationView(baseInsight());
    expect(view).toEqual({
      context: 'homeoffice',
      withN: 12,
      withoutN: 18,
      withGood: 8,
      withoutGood: 6,
      effectSurvives: true,
      weekdayHeldCoefficient: 0.31,
      calendarHeldCoefficient: 0.22,
    });
  });

  it('returns null when stratum is incomplete', () => {
    expect(
      parseSameSituationView(
        baseInsight({
          same_work_context_without_n: 0,
        })
      )
    ).toBeNull();
  });
});
