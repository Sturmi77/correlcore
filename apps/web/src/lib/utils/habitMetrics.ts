import type { HabitStatsResponse } from '$lib/api/habits';

/** Minimum calendar-window days before showing full adherence interpretation. */
export const MIN_HABIT_CALENDAR_DAYS = 7;

const METRIC_I18N_SUFFIX: Record<string, string> = {
  mood_score: 'mood',
  mood_avg: 'mood',
  mood: 'mood',
  energy: 'energy',
  energy_avg: 'energy',
  stress: 'stress',
  stress_avg: 'stress',
};

export function habitMetricI18nKey(metric: string | null | undefined): string {
  if (!metric) return '';
  const suffix = METRIC_I18N_SUFFIX[metric] ?? metric;
  return `trends.metric.${suffix}`;
}

/**
 * Whether adherence stats should stay behind the neutral "keep tracking" copy.
 * Uses target-aware thresholding so low-frequency habits are not gated on 7 occurrences.
 */
export function isHabitAdherenceInsufficient(habit: HabitStatsResponse): boolean {
  if (habit.days_tracked === 0) {
    return true;
  }
  const threshold = Math.min(MIN_HABIT_CALENDAR_DAYS, habit.target_days);
  return habit.days_tracked < threshold;
}

export function habitStatusI18nKey(habit: HabitStatsResponse): string {
  if (habit.habit_type === 'reduce') {
    return habit.days_tracked <= habit.target_days
      ? 'habits.status.within_target'
      : 'habits.status.above_target';
  }
  return 'habits.status.progress';
}

export function habitGoalI18nKey(habit: HabitStatsResponse): string {
  return habit.habit_type === 'reduce' ? 'habits.goal.reduce' : 'habits.goal.build';
}

export function habitProgressValue(habit: HabitStatsResponse): number {
  return Math.max(0, Math.min(100, Math.round(habit.adherence_rate)));
}

export function formatHabitDelta(delta: number): string {
  const rounded = Math.round(delta);
  if (rounded > 0) return `+${rounded}`;
  return `${rounded}`;
}
