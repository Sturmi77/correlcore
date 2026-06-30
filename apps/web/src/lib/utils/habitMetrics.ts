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
