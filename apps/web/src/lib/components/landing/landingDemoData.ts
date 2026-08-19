/**
 * Static demo fixtures for the anonymous marketing landing.
 * No auth/API — representative product shots only.
 */
import type {
  InsightMaturity,
  InsightResponse,
  TagClustersResponse,
  TagCooccurrenceResponse,
} from '$lib/api/insights';
import type { WeekdaySummaryItem } from '$lib/api/dashboard';
import type { TimeseriesPoint } from '$lib/api/stats';

export const landingTagClusters: TagClustersResponse = {
  status: 'ok',
  entry_count: 60,
  active_tag_count: 6,
  active_signal_count: 7,
  window_days: 90,
  k: 2,
  reason: null,
  cluster_kind: 'mixed',
  cluster_maturity: 'provisional',
  cluster_mode: 'kmeans',
  entries_until_robust: 30,
  silhouette_score: 0.18,
  clusters: [
    {
      cluster_id: 1,
      label: 'Poor-sleep cluster',
      cluster_kind: 'mixed',
      strength: 0.74,
      tags: [
        {
          tag_id: 'demo-poor-sleep',
          slug: 'poor-sleep',
          name: 'Poor sleep',
          category: 'sleep',
          color: null,
        },
        {
          tag_id: 'demo-low-energy',
          slug: 'low-energy',
          name: 'Low energy',
          category: 'energy',
          color: null,
        },
      ],
      members: [
        {
          kind: 'tag',
          signal_id: 'demo-poor-sleep',
          slug: 'poor-sleep',
          name: 'Poor sleep',
          category: 'sleep',
          color: null,
        },
        {
          kind: 'symptom',
          signal_id: 'demo-headache',
          slug: 'headache',
          name: 'Headache',
          category: 'symptom',
          color: null,
          icon: '🤕',
        },
        {
          kind: 'tag',
          signal_id: 'demo-low-energy',
          slug: 'low-energy',
          name: 'Low energy',
          category: 'energy',
          color: null,
        },
      ],
    },
    {
      cluster_id: 2,
      label: 'Active days',
      cluster_kind: 'tags_only',
      strength: 0.68,
      tags: [
        {
          tag_id: 'demo-exercise',
          slug: 'exercise',
          name: 'Exercise',
          category: 'activity',
          color: null,
        },
        {
          tag_id: 'demo-good-mood',
          slug: 'good-mood',
          name: 'Good mood',
          category: 'mood',
          color: null,
        },
      ],
      members: [
        {
          kind: 'tag',
          signal_id: 'demo-exercise',
          slug: 'exercise',
          name: 'Exercise',
          category: 'activity',
          color: null,
        },
        {
          kind: 'tag',
          signal_id: 'demo-good-mood',
          slug: 'good-mood',
          name: 'Good mood',
          category: 'mood',
          color: null,
        },
      ],
    },
  ],
};

export const landingTimeseriesPoints: TimeseriesPoint[] = [
  {
    period_start: '2026-07-13',
    period_end: '2026-07-13',
    entry_count: 1,
    mood_avg: 3.2,
    energy_avg: 3.0,
    stress_avg: 2.8,
    sleep_quality_avg: 3.0,
  },
  {
    period_start: '2026-07-14',
    period_end: '2026-07-14',
    entry_count: 1,
    mood_avg: 3.6,
    energy_avg: 3.4,
    stress_avg: 2.5,
    sleep_quality_avg: 3.5,
  },
  {
    period_start: '2026-07-15',
    period_end: '2026-07-15',
    entry_count: 1,
    mood_avg: 3.1,
    energy_avg: 2.9,
    stress_avg: 3.2,
    sleep_quality_avg: 2.5,
  },
  {
    period_start: '2026-07-16',
    period_end: '2026-07-16',
    entry_count: 1,
    mood_avg: 3.9,
    energy_avg: 3.7,
    stress_avg: 2.2,
    sleep_quality_avg: 4.0,
  },
  {
    period_start: '2026-07-17',
    period_end: '2026-07-17',
    entry_count: 1,
    mood_avg: 4.1,
    energy_avg: 3.8,
    stress_avg: 2.0,
    sleep_quality_avg: 4.5,
  },
  {
    period_start: '2026-07-18',
    period_end: '2026-07-18',
    entry_count: 1,
    mood_avg: 3.7,
    energy_avg: 3.5,
    stress_avg: 2.4,
    sleep_quality_avg: 3.5,
  },
  {
    period_start: '2026-07-19',
    period_end: '2026-07-19',
    entry_count: 1,
    mood_avg: 3.8,
    energy_avg: 3.6,
    stress_avg: 2.3,
    sleep_quality_avg: 4.0,
  },
];

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

/** Representative insight rows for the marketing Insight Matrix product shot. */
export const landingInsights: InsightResponse[] = [
  demoInsight({
    id: 'demo-exercise-mood',
    subject_id: 'demo-exercise',
    subject_label: 'Exercise',
    metric: 'mood_score',
    effect_size: 0.42,
    confidence: 0.81,
    statement: 'Days with exercise tend to show higher mood.',
    payload: { tag_slug: 'exercise', tag_name: 'Exercise' },
  }),
  demoInsight({
    id: 'demo-sleep-mood',
    subject_id: 'demo-poor-sleep',
    subject_label: 'Poor sleep',
    metric: 'mood_score',
    effect_size: -0.31,
    confidence: 0.68,
    statement: 'Poor-sleep days tend to show lower mood.',
    payload: { tag_slug: 'poor-sleep', tag_name: 'Poor sleep' },
  }),
  demoInsight({
    id: 'demo-coffee-energy',
    subject_id: 'demo-coffee',
    subject_label: 'Coffee',
    metric: 'energy',
    effect_size: 0.24,
    confidence: 0.55,
    statement: 'Coffee days tend to show slightly higher energy.',
    payload: { tag_slug: 'coffee', tag_name: 'Coffee' },
  }),
];

/** Strongest insight, used for the standalone Insight Card product shot. */
export const landingFeaturedInsight: InsightResponse = landingInsights[0];

/**
 * Lag-correlation product shot (#488). `LagCorrelationHeatmap` renders one row
 * per feature→target pair and needs `payload.method === 'lag'` with a
 * `lag_profile` of ≥ 2 `{lag, r}` points; it self-hides below two rows, so we
 * ship two pairs. Targets use core-metric keys (`mood_score`, `energy`) so the
 * component translates them to localized metric names. This is the app's key
 * differentiator — showing *with what time delay* a factor acts.
 */
export const landingLagInsights: InsightResponse[] = [
  demoInsight({
    id: 'demo-lag-sleep-mood',
    insight_type: 'lag',
    subject_id: 'demo-poor-sleep',
    subject_label: 'Poor sleep',
    metric: 'mood_score',
    effect_size: 0.62,
    confidence: 0.74,
    statement: 'Poor sleep tends to lower mood about two days later.',
    payload: {
      method: 'lag',
      lag_days: 2,
      feature: { name: 'Poor sleep', key: 'poor-sleep', kind: 'tag' },
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
    subject_label: 'Exercise',
    metric: 'energy',
    effect_size: 0.55,
    confidence: 0.7,
    statement: 'Exercise tends to raise energy the next day.',
    payload: {
      method: 'lag',
      lag_days: 1,
      feature: { name: 'Exercise', key: 'exercise', kind: 'tag' },
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

export const landingMaturity: InsightMaturity = {
  phase: 'robust',
  phase_index: 4,
  current_entries: 92,
  next_phase_at: null,
  next_phase_label: null,
  entries_until_next: null,
  user_message_key: 'insights.maturity.robust',
};

/**
 * Weekday product shot (A3). `HomeWeekdayOverview` derives its bars from a
 * `weekday_summary` (index 0 = Monday) plus an optional `weekday_pattern`
 * insight for the tier badge + statement. Labels stay in English to match the
 * other product shots. Friday is the high day, Saturday the low — so the
 * best/worst highlights both fire.
 */
export const landingWeekdaySummary: WeekdaySummaryItem[] = [
  { weekday: 0, entry_count: 9, mood_avg: 3.4, top_signal: null },
  { weekday: 1, entry_count: 9, mood_avg: 3.6, top_signal: null },
  {
    weekday: 2,
    entry_count: 9,
    mood_avg: 3.9,
    top_signal: { kind: 'tag', id: 'demo-home-office', label: 'Home office', count: 6, share: 0.7 },
  },
  { weekday: 3, entry_count: 9, mood_avg: 3.5, top_signal: null },
  {
    weekday: 4,
    entry_count: 9,
    mood_avg: 4.2,
    top_signal: { kind: 'tag', id: 'demo-exercise', label: 'Exercise', count: 7, share: 0.78 },
  },
  {
    weekday: 5,
    entry_count: 8,
    mood_avg: 3.1,
    top_signal: { kind: 'tag', id: 'demo-poor-sleep', label: 'Poor sleep', count: 5, share: 0.63 },
  },
  { weekday: 6, entry_count: 8, mood_avg: 3.3, top_signal: null },
];

export const landingWeekdayInsight: InsightResponse = demoInsight({
  id: 'demo-weekday-pattern',
  insight_type: 'weekday_pattern',
  subject_type: 'weekday',
  subject_id: 'demo-friday',
  subject_label: 'Friday',
  metric: 'mood_score',
  effect_size: 0.44,
  confidence: 0.62,
  statement: 'Fridays tend to show the highest mood.',
  payload: {
    weekday: 4,
    weekday_mood_avgs: { '0': 3.4, '1': 3.6, '2': 3.9, '3': 3.5, '4': 4.2, '5': 3.1, '6': 3.3 },
  },
});

function cooRef(tag_id: string, slug: string, name: string) {
  return { tag_id, slug, name, category: 'demo', color: null };
}

/**
 * Pairs for the Tag Co-occurrence heatmap product shot. Kept to four tags so the
 * grid fills the narrow marketing frame without horizontal overflow (#546) while
 * every off-diagonal cell carries a value — a dense, legible mini heatmap.
 */
export const landingCooccurrence: TagCooccurrenceResponse = {
  range: '90d',
  start_date: '2026-04-20',
  end_date: '2026-07-19',
  min_count: 2,
  pairs: [
    {
      tag_a: cooRef('demo-poor-sleep', 'poor-sleep', 'Poor sleep'),
      tag_b: cooRef('demo-low-energy', 'low-energy', 'Low energy'),
      count: 9,
      pct_of_a: 75,
      pct_of_b: 64,
    },
    {
      tag_a: cooRef('demo-poor-sleep', 'poor-sleep', 'Poor sleep'),
      tag_b: cooRef('demo-headache', 'headache', 'Headache'),
      count: 6,
      pct_of_a: 50,
      pct_of_b: 60,
    },
    {
      tag_a: cooRef('demo-poor-sleep', 'poor-sleep', 'Poor sleep'),
      tag_b: cooRef('demo-exercise', 'exercise', 'Exercise'),
      count: 2,
      pct_of_a: 17,
      pct_of_b: 18,
    },
    {
      tag_a: cooRef('demo-low-energy', 'low-energy', 'Low energy'),
      tag_b: cooRef('demo-headache', 'headache', 'Headache'),
      count: 5,
      pct_of_a: 42,
      pct_of_b: 50,
    },
    {
      tag_a: cooRef('demo-low-energy', 'low-energy', 'Low energy'),
      tag_b: cooRef('demo-exercise', 'exercise', 'Exercise'),
      count: 3,
      pct_of_a: 25,
      pct_of_b: 27,
    },
    {
      tag_a: cooRef('demo-headache', 'headache', 'Headache'),
      tag_b: cooRef('demo-exercise', 'exercise', 'Exercise'),
      count: 2,
      pct_of_a: 20,
      pct_of_b: 18,
    },
  ],
};
