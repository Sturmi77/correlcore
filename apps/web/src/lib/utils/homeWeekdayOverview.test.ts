import { describe, expect, it } from 'vitest';
import { buildWeekdayOverviewCells, hasWeekdayOverviewContent } from './homeWeekdayOverview';
import type { InsightResponse } from '$lib/api/insights';

function makeInsight(partial: Partial<InsightResponse>): InsightResponse {
  return {
    id: 'insight-1',
    user_id: 'user-1',
    insight_type: 'pointbiserial',
    tier: 'early',
    metric: 'mood_score',
    subject_type: 'tag',
    subject_id: 'tag-1',
    subject_label: 'Running',
    effect_size: 0.4,
    confidence: 0.3,
    sample_n: 10,
    statement: 'Pattern',
    flags: { weekday_confounded: true },
    payload: {},
    generated_for_date: '2026-07-01',
    generated_at: '2026-07-01T00:00:00Z',
    created_at: '2026-07-01T00:00:00Z',
    updated_at: '2026-07-01T00:00:00Z',
    ...partial,
  };
}

describe('homeWeekdayOverview', () => {
  it('maps mood averages and weekday-confounded findings', () => {
    const cells = buildWeekdayOverviewCells([
      makeInsight({
        insight_type: 'weekday_pattern',
        subject_type: 'weekday',
        payload: {
          weekday_mood_avgs: { '0': 4.2, '2': 2.1 },
        },
      }),
      makeInsight({
        subject_label: 'Tuesday running',
        payload: { weekday: 1 },
      }),
      makeInsight({
        subject_label: 'Headache',
        subject_type: 'symptom',
        payload: { weekday: 2 },
      }),
    ]);

    expect(cells[0].moodAvg).toBe(4.2);
    expect(cells[1].findingLabel).toBe('Tuesday running');
    expect(cells[2].findingLabel).toBe('Headache');
    expect(hasWeekdayOverviewContent(cells)).toBe(true);
  });
});
