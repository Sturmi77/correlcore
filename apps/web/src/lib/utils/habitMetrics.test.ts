import { describe, expect, it } from 'vitest';
import type { HabitStatsResponse } from '$lib/api/habits';
import {
  formatHabitDelta,
  habitGoalI18nKey,
  habitMetricI18nKey,
  habitProgressValue,
  habitStatusI18nKey,
  habitTypeGlyph,
  groupHabitsByType,
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
    previous_adherence_rate: null,
    adherence_delta: null,
    trend_direction: 'unknown',
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

describe('habit status helpers', () => {
  it('maps build and reduce goals to i18n keys', () => {
    expect(habitGoalI18nKey(habit({ habit_type: 'build' }))).toBe('habits.goal.build');
    expect(habitGoalI18nKey(habit({ habit_type: 'reduce' }))).toBe('habits.goal.reduce');
  });

  it('describes reduce habits by target range', () => {
    expect(
      habitStatusI18nKey(habit({ habit_type: 'reduce', days_tracked: 2, target_days: 3 }))
    ).toBe('habits.status.within_target');
    expect(
      habitStatusI18nKey(habit({ habit_type: 'reduce', days_tracked: 4, target_days: 3 }))
    ).toBe('habits.status.above_target');
  });

  it('rounds visual progress and clamps it to meter bounds', () => {
    expect(habitProgressValue(habit({ adherence_rate: 62.5 }))).toBe(63);
    expect(habitProgressValue(habit({ adherence_rate: 120 }))).toBe(100);
  });

  it('formats percentage point deltas with a plus sign only when positive', () => {
    expect(formatHabitDelta(12.5)).toBe('+13');
    expect(formatHabitDelta(-4.8)).toBe('-5');
    expect(formatHabitDelta(0)).toBe('0');
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

describe('build vs reduce encoding (#490)', () => {
  it('keeps "fuller = better" for both types', () => {
    // adherence_rate is already normalised server-side: a reduce habit inside
    // its limit returns 100. Inverting the value here would show a
    // well-managed reduce habit as an almost empty bar.
    const buildOnTrack = habit({ habit_type: 'build', adherence_rate: 100 });
    const reduceWithinLimit = habit({
      habit_type: 'reduce',
      adherence_rate: 100,
      days_tracked: 2,
      target_days: 4,
    });
    expect(habitProgressValue(buildOnTrack)).toBe(100);
    expect(habitProgressValue(reduceWithinLimit)).toBe(100);
  });

  it('shows a reduce habit over its limit as a low bar', () => {
    const overLimit = habit({ habit_type: 'reduce', adherence_rate: 12, days_tracked: 20 });
    expect(habitProgressValue(overLimit)).toBe(12);
  });

  it('splits rows into stable build and reduce sections', () => {
    const rows = [
      { habit: habit({ tag_id: 'a', habit_type: 'reduce' }) },
      { habit: habit({ tag_id: 'b', habit_type: 'build' }) },
      { habit: habit({ tag_id: 'c', habit_type: 'reduce' }) },
    ];
    const groups = groupHabitsByType(rows);
    expect(groups.build.map((r) => r.habit.tag_id)).toEqual(['b']);
    expect(groups.reduce.map((r) => r.habit.tag_id)).toEqual(['a', 'c']);
  });

  it('always returns both group keys so section order stays stable', () => {
    const groups = groupHabitsByType([]);
    expect(Object.keys(groups).sort()).toEqual(['build', 'reduce']);
    expect(groups.build).toEqual([]);
    expect(groups.reduce).toEqual([]);
  });

  it('uses a distinct glyph per type', () => {
    expect(habitTypeGlyph(habit({ habit_type: 'build' }))).toBe('+');
    expect(habitTypeGlyph(habit({ habit_type: 'reduce' }))).toBe('−');
  });
});
