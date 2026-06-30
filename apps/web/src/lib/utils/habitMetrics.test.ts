import { describe, expect, it } from 'vitest';
import type { HabitStatsResponse } from '$lib/api/habits';
import {
  habitMetricI18nKey,
  isHabitAdherenceInsufficient,
  MIN_HABIT_CALENDAR_DAYS,
} from './habitMetrics';

function habit(overrides: Partial<HabitStatsResponse> = {}): HabitStatsResponse {
  return {
    tag_id: 'tag-1',
    habit_type: 'build',
    target_frequency: 4,
    window: 28,
    start_date: '2026-05-01',
    end_date: '2026-05-28',
    days_tracked: 10,
    days_total: 28,
    target_days: 16,
    adherence_rate: 62.5,
    correlation_score: null,
    correlation_metric: null,
    ...overrides,
  };
}

describe('habitMetricI18nKey', () => {
  it('maps API metric keys to trends i18n suffixes', () => {
    expect(habitMetricI18nKey('mood_score')).toBe('trends.metric.mood');
    expect(habitMetricI18nKey('energy')).toBe('trends.metric.energy');
    expect(habitMetricI18nKey('stress_avg')).toBe('trends.metric.stress');
  });
});

describe('isHabitAdherenceInsufficient', () => {
  it('requires at least one tracked day', () => {
    expect(isHabitAdherenceInsufficient(habit({ days_tracked: 0, target_days: 16 }))).toBe(true);
  });

  it('allows met low-frequency build habits before seven occurrences', () => {
    expect(
      isHabitAdherenceInsufficient(
        habit({ window: 7, days_total: 7, target_days: 3, days_tracked: 3, adherence_rate: 100 })
      )
    ).toBe(false);
  });

  it('keeps high-target habits gated until seven tracked days', () => {
    expect(
      isHabitAdherenceInsufficient(
        habit({ target_days: 16, days_tracked: 2, adherence_rate: 12.5 })
      )
    ).toBe(true);
    expect(
      isHabitAdherenceInsufficient(
        habit({ target_days: 16, days_tracked: 7, adherence_rate: 43.8 })
      )
    ).toBe(false);
  });

  it('uses the shared calendar minimum constant', () => {
    expect(MIN_HABIT_CALENDAR_DAYS).toBe(7);
  });
});
