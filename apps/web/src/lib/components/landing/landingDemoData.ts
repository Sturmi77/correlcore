/**
 * Demo fixtures for the anonymous marketing landing.
 * No auth/API — representative product shots only.
 *
 * Human-readable strings (tag names, insight statements, weekday signals)
 * are resolved from i18n via `buildLandingDemo`, so the product shots follow
 * the active locale. Structural/numeric data stays static.
 *
 * #735 I8: each shot tells a different story (exercise→mood, sleep lag,
 * Friday weekday) so the page does not chew the same fake numbers five times.
 */
import type { InsightMaturity, InsightResponse } from '$lib/api/insights';
import type { WeekdaySummaryItem } from '$lib/api/dashboard';

/** Minimal translate signature (svelte-i18n's `$_`), keyed by message id. */
export type TranslateFn = (key: string) => string;

export const landingMaturity: InsightMaturity = {
  phase: 'robust',
  phase_index: 4,
  current_entries: 92,
  next_phase_at: null,
  next_phase_label: null,
  entries_until_next: null,
  user_message_key: 'insights.maturity.robust',
};

function demoInsight(overrides: Partial<InsightResponse>): InsightResponse {
  return {
    id: 'demo',
    user_id: 'demo',
    insight_type: 'pointbiserial',
    tier: 'robust',
    metric: 'mood_score',
    subject_type: 'tag',
    subject_id: 'demo',
    subject_label: 'Tag',
    effect_size: 0.3,
    confidence: 0.7,
    sample_n: 60,
    statement: null,
    flags: {},
    payload: {},
    generated_for_date: '2026-07-19',
    generated_at: '2026-07-19T08:00:00Z',
    created_at: '2026-07-19T08:00:00Z',
    updated_at: '2026-07-19T08:00:00Z',
    ...overrides,
  };
}

export interface LandingDemo {
  featuredInsight: InsightResponse;
  lagInsights: InsightResponse[];
  maturity: InsightMaturity;
  weekdaySummary: WeekdaySummaryItem[];
  weekdayInsight: InsightResponse;
}

export function buildLandingDemo(t: TranslateFn): LandingDemo {
  const poorSleep = t('landing.demo.poor_sleep');
  const exercise = t('landing.demo.exercise');
  const homeOffice = t('landing.demo.home_office');
  const friday = t('landing.demo.friday');

  const featuredInsight = demoInsight({
    id: 'demo-exercise-mood',
    subject_id: 'demo-exercise',
    subject_label: exercise,
    metric: 'mood_score',
    effect_size: 0.42,
    confidence: 0.81,
    statement: t('landing.demo.stmt_exercise_mood'),
    payload: { tag_slug: 'exercise', tag_name: exercise },
  });

  const lagInsights: InsightResponse[] = [
    demoInsight({
      id: 'demo-lag-sleep-mood',
      insight_type: 'lag',
      subject_id: 'demo-poor-sleep',
      subject_label: poorSleep,
      metric: 'mood_score',
      effect_size: 0.62,
      confidence: 0.74,
      statement: t('landing.demo.stmt_lag_sleep_mood'),
      payload: {
        method: 'lag',
        lag_days: 2,
        feature: { name: poorSleep, key: 'poor-sleep', kind: 'tag' },
        target: { name: 'Mood', key: 'mood_score', kind: 'metric' },
        lag_profile: [
          { lag: 1, r: -0.28 },
          { lag: 2, r: -0.62 },
          { lag: 3, r: -0.41 },
          { lag: 4, r: -0.19 },
          { lag: 5, r: -0.08 },
        ],
      },
    }),
    demoInsight({
      id: 'demo-lag-exercise-energy',
      insight_type: 'lag',
      subject_id: 'demo-exercise',
      subject_label: exercise,
      metric: 'energy',
      effect_size: 0.55,
      confidence: 0.7,
      statement: t('landing.demo.stmt_lag_exercise_energy'),
      payload: {
        method: 'lag',
        lag_days: 1,
        feature: { name: exercise, key: 'exercise', kind: 'tag' },
        target: { name: 'Energy', key: 'energy', kind: 'metric' },
        lag_profile: [
          { lag: 1, r: 0.55 },
          { lag: 2, r: 0.38 },
          { lag: 3, r: 0.22 },
          { lag: 4, r: 0.1 },
        ],
      },
    }),
  ];

  const weekdaySummary: WeekdaySummaryItem[] = [
    { weekday: 0, entry_count: 9, mood_avg: 3.4, top_signal: null },
    { weekday: 1, entry_count: 9, mood_avg: 3.6, top_signal: null },
    {
      weekday: 2,
      entry_count: 9,
      mood_avg: 3.9,
      top_signal: {
        kind: 'tag',
        id: 'demo-home-office',
        label: homeOffice,
        count: 6,
        share: 0.7,
      },
    },
    { weekday: 3, entry_count: 9, mood_avg: 3.5, top_signal: null },
    {
      weekday: 4,
      entry_count: 9,
      mood_avg: 4.2,
      top_signal: { kind: 'tag', id: 'demo-exercise', label: exercise, count: 7, share: 0.78 },
    },
    {
      weekday: 5,
      entry_count: 8,
      mood_avg: 3.1,
      top_signal: { kind: 'tag', id: 'demo-poor-sleep', label: poorSleep, count: 5, share: 0.63 },
    },
    { weekday: 6, entry_count: 8, mood_avg: 3.3, top_signal: null },
  ];

  const weekdayInsight = demoInsight({
    id: 'demo-weekday-pattern',
    insight_type: 'weekday_pattern',
    subject_type: 'weekday',
    subject_id: 'demo-friday',
    subject_label: friday,
    metric: 'mood_score',
    effect_size: 0.44,
    confidence: 0.62,
    statement: t('landing.demo.stmt_weekday_friday'),
    payload: {
      weekday: 4,
      weekday_mood_avgs: { '0': 3.4, '1': 3.6, '2': 3.9, '3': 3.5, '4': 4.2, '5': 3.1, '6': 3.3 },
    },
  });

  return {
    featuredInsight,
    lagInsights,
    maturity: landingMaturity,
    weekdaySummary,
    weekdayInsight,
  };
}
