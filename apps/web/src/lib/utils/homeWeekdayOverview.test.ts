import { describe, expect, it } from 'vitest';
import {
  buildWeekdayOverviewCells,
  hasWeekdayOverviewContent,
  selectNewestWeekdayPattern,
} from './homeWeekdayOverview';
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
    const cells = buildWeekdayOverviewCells(
      [
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
      ],
      []
    );

    expect(cells[0].moodAvg).toBe(4.2);
    expect(cells[1].findingLabel).toBe('Tuesday running');
    expect(cells[2].findingLabel).toBe('Headache');
    expect(hasWeekdayOverviewContent(cells)).toBe(true);
  });

  it('renders bars from dashboard weekday_summary without weekday_pattern insight', () => {
    const cells = buildWeekdayOverviewCells(
      [],
      [
        { weekday: 0, entry_count: 10, mood_avg: 3.1 },
        { weekday: 1, entry_count: 9, mood_avg: 3.0 },
        { weekday: 2, entry_count: 10, mood_avg: 3.2 },
        { weekday: 3, entry_count: 9, mood_avg: 3.1 },
        { weekday: 4, entry_count: 10, mood_avg: 3.8 },
        { weekday: 5, entry_count: 9, mood_avg: 3.3 },
        { weekday: 6, entry_count: 10, mood_avg: 3.0 },
      ]
    );

    expect(cells.every((cell) => cell.moodAvg !== null)).toBe(true);
    expect(cells[4].moodAvg).toBe(3.8);
    expect(hasWeekdayOverviewContent(cells)).toBe(true);
  });

  it('prefers dashboard weekday_summary over insight weekday_mood_avgs', () => {
    const cells = buildWeekdayOverviewCells(
      [
        makeInsight({
          insight_type: 'weekday_pattern',
          payload: { weekday_mood_avgs: { '4': 2.0 } },
        }),
      ],
      [{ weekday: 4, entry_count: 10, mood_avg: 3.8 }]
    );

    expect(cells[4].moodAvg).toBe(3.8);
  });
});

describe('selectNewestWeekdayPattern', () => {
  it('returns null when there is no weekday_pattern insight', () => {
    const insights = [makeInsight({ subject_label: 'Running' })];
    expect(selectNewestWeekdayPattern(insights)).toBeNull();
  });

  it('picks the most recently generated weekday_pattern, not the highest-ranked one', () => {
    // Regression: /insights/latest keys weekday_pattern rows by weekday label
    // (subject_id is always null), so an older "Wednesday" row and a newer
    // "Friday" row can both survive backend dedup. rankInsights sorts by
    // confidence × |effect_size|, so a caller that just takes the top-ranked
    // match can surface the stale one.
    const staleHighScore = makeInsight({
      id: 'stale-wednesday',
      insight_type: 'weekday_pattern',
      subject_type: 'weekday',
      subject_label: 'Wednesday',
      confidence: 0.9,
      effect_size: 0.8,
      generated_for_date: '2026-06-01',
    });
    const freshLowScore = makeInsight({
      id: 'fresh-friday',
      insight_type: 'weekday_pattern',
      subject_type: 'weekday',
      subject_label: 'Friday',
      confidence: 0.3,
      effect_size: 0.24,
      generated_for_date: '2026-07-10',
    });

    // Order mimics rankInsights output: highest score first.
    const result = selectNewestWeekdayPattern([staleHighScore, freshLowScore]);
    expect(result?.id).toBe('fresh-friday');
  });

  it('ignores non-weekday_pattern insights mixed into the list', () => {
    const weekday = makeInsight({
      id: 'weekday-only',
      insight_type: 'weekday_pattern',
      subject_type: 'weekday',
      generated_for_date: '2026-07-05',
    });
    const other = makeInsight({ id: 'unrelated-tag', generated_for_date: '2026-07-12' });

    expect(selectNewestWeekdayPattern([other, weekday])?.id).toBe('weekday-only');
  });
});

describe('top signal vs confounder precedence (#487)', () => {
  const summary = (weekday: number, label: string | null) => ({
    weekday,
    entry_count: 10,
    mood_avg: 3.2,
    top_signal: label ? { kind: 'tag' as const, id: 't1', label, count: 5, share: 0.5 } : null,
  });

  it('fills a day that has no confounder with the top signal', () => {
    const cells = buildWeekdayOverviewCells([], [summary(2, 'Meeting')]);
    const wednesday = cells[2];
    expect(wednesday.findingLabel).toBe('Meeting');
    expect(wednesday.findingType).toBe('tag');
    expect(wednesday.findingSource).toBe('top_signal');
  });

  it('lets the confounder win where both exist', () => {
    // The confounder is the rarer, stronger statement — it must not be
    // displaced by a purely descriptive frequency.
    const cells = buildWeekdayOverviewCells(
      [makeInsight({ payload: { weekday: 2 }, subject_label: 'Running' })],
      [summary(2, 'Meeting')]
    );
    expect(cells[2].findingLabel).toBe('Running');
    expect(cells[2].findingSource).toBe('confounder');
  });

  it('maps top-signal kinds onto the existing finding types', () => {
    const kinds = [
      ['tag', 'tag'],
      ['symptom', 'symptom'],
      ['work_context', 'context'],
    ] as const;
    for (const [kind, expected] of kinds) {
      const cells = buildWeekdayOverviewCells(
        [],
        [
          {
            weekday: 0,
            entry_count: 10,
            mood_avg: null,
            top_signal: { kind, id: null, label: 'X', count: 4, share: 0.4 },
          },
        ]
      );
      expect(cells[0].findingType).toBe(expected);
    }
  });

  it('leaves the day empty when neither source has anything', () => {
    const cells = buildWeekdayOverviewCells([], [summary(3, null)]);
    expect(cells[3].findingLabel).toBeNull();
    expect(cells[3].findingSource).toBeNull();
  });
});
