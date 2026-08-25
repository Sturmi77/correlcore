/**
 * Demo fixtures for the anonymous marketing landing.
 * No auth/API — representative product shots only.
 *
 * B4 (#734): the human-readable strings (tag names, cluster labels, insight
 * statements, weekday signals) are resolved from i18n via `buildLandingDemo`,
 * so the product shots follow the active locale instead of being hard-coded in
 * English while the UI chrome is German. Structural/numeric data stays static.
 */
import type {
  InsightMaturity,
  InsightResponse,
  TagClustersResponse,
  TagCooccurrenceResponse,
} from '$lib/api/insights';
import type { WeekdaySummaryItem } from '$lib/api/dashboard';
import type { TimeseriesPoint } from '$lib/api/stats';

/** Minimal translate signature (svelte-i18n's `$_`), keyed by message id. */
export type TranslateFn = (key: string) => string;

/** Locale-independent timeseries for the trends product shot. */
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

/**
 * Hero strip series (A4). A denser multi-week wave — sleep dips drag mood and
 * energy down a day or two later while stress rises, then everything recovers —
 * so the divergent strip reads as the actual correlation story rather than a
 * flat band. Kept separate from `landingTimeseriesPoints` so the bento
 * week-timeseries shot is unchanged. Values are display-space 1–5 (stress is
 * inverted inside the strip), one entry per day.
 */
const STRIP_WAVE: ReadonlyArray<
  readonly [sleep: number, mood: number, energy: number, stress: number]
> = [
  [4.1, 3.9, 3.7, 2.1],
  [4.3, 4.0, 3.8, 2.0],
  [3.4, 3.5, 3.4, 2.5],
  [2.8, 3.1, 3.0, 3.0],
  [2.3, 2.6, 2.5, 3.6],
  [2.0, 2.3, 2.3, 3.9],
  [2.6, 2.7, 2.6, 3.4],
  [3.3, 3.1, 3.0, 2.8],
  [3.9, 3.6, 3.5, 2.4],
  [4.3, 3.9, 3.8, 2.0],
  [3.8, 3.9, 3.8, 2.2],
  [3.2, 3.4, 3.3, 2.7],
  [3.9, 3.7, 3.6, 2.2],
  [4.5, 4.2, 4.0, 1.8],
];

/** ISO date `offset` days before `end` (UTC, no wall-clock drift). */
function isoDaysBefore(end: string, offset: number): string {
  const date = new Date(`${end}T00:00:00Z`);
  date.setUTCDate(date.getUTCDate() - offset);
  return date.toISOString().slice(0, 10);
}

/** Locale-independent hero strip fixture — ends on the same day as the rest. */
export const landingStripPoints: TimeseriesPoint[] = STRIP_WAVE.map(
  ([sleep, mood, energy, stress], index) => {
    const period = isoDaysBefore('2026-07-19', STRIP_WAVE.length - 1 - index);
    return {
      period_start: period,
      period_end: period,
      entry_count: 1,
      mood_avg: mood,
      energy_avg: energy,
      stress_avg: stress,
      sleep_quality_avg: sleep,
    };
  }
);

/** Axis keys for the hero strip, aligned to `landingStripPoints`. */
export const landingStripAxisDates: string[] = landingStripPoints.map((p) => p.period_start);

/** Locale-independent maturity fixture (renders via a message key). */
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

function cooRef(tag_id: string, slug: string, name: string) {
  return { tag_id, slug, name, category: 'demo', color: null };
}

export interface LandingDemo {
  tagClusters: TagClustersResponse;
  timeseriesPoints: TimeseriesPoint[];
  stripPoints: TimeseriesPoint[];
  stripAxisDates: string[];
  insights: InsightResponse[];
  featuredInsight: InsightResponse;
  lagInsights: InsightResponse[];
  maturity: InsightMaturity;
  weekdaySummary: WeekdaySummaryItem[];
  weekdayInsight: InsightResponse;
  cooccurrence: TagCooccurrenceResponse;
}

/**
 * Build the landing product-shot fixtures with localized human strings.
 * Call reactively with the active `$_` so the shots re-render on locale change.
 */
export function buildLandingDemo(t: TranslateFn): LandingDemo {
  const L = {
    poorSleep: t('landing.demo.poor_sleep'),
    lowEnergy: t('landing.demo.low_energy'),
    headache: t('landing.demo.headache'),
    exercise: t('landing.demo.exercise'),
    goodMood: t('landing.demo.good_mood'),
    coffee: t('landing.demo.coffee'),
    homeOffice: t('landing.demo.home_office'),
    friday: t('landing.demo.friday'),
    clusterPoorSleep: t('landing.demo.cluster_poor_sleep'),
    clusterActive: t('landing.demo.cluster_active'),
  };

  const tagClusters: TagClustersResponse = {
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
        label: L.clusterPoorSleep,
        cluster_kind: 'mixed',
        strength: 0.74,
        tags: [
          {
            tag_id: 'demo-poor-sleep',
            slug: 'poor-sleep',
            name: L.poorSleep,
            category: 'sleep',
            color: null,
          },
          {
            tag_id: 'demo-low-energy',
            slug: 'low-energy',
            name: L.lowEnergy,
            category: 'energy',
            color: null,
          },
        ],
        members: [
          {
            kind: 'tag',
            signal_id: 'demo-poor-sleep',
            slug: 'poor-sleep',
            name: L.poorSleep,
            category: 'sleep',
            color: null,
          },
          {
            kind: 'symptom',
            signal_id: 'demo-headache',
            slug: 'headache',
            name: L.headache,
            category: 'symptom',
            color: null,
            icon: '🤕',
          },
          {
            kind: 'tag',
            signal_id: 'demo-low-energy',
            slug: 'low-energy',
            name: L.lowEnergy,
            category: 'energy',
            color: null,
          },
        ],
      },
      {
        cluster_id: 2,
        label: L.clusterActive,
        cluster_kind: 'tags_only',
        strength: 0.68,
        tags: [
          {
            tag_id: 'demo-exercise',
            slug: 'exercise',
            name: L.exercise,
            category: 'activity',
            color: null,
          },
          {
            tag_id: 'demo-good-mood',
            slug: 'good-mood',
            name: L.goodMood,
            category: 'mood',
            color: null,
          },
        ],
        members: [
          {
            kind: 'tag',
            signal_id: 'demo-exercise',
            slug: 'exercise',
            name: L.exercise,
            category: 'activity',
            color: null,
          },
          {
            kind: 'tag',
            signal_id: 'demo-good-mood',
            slug: 'good-mood',
            name: L.goodMood,
            category: 'mood',
            color: null,
          },
        ],
      },
    ],
  };

  const insights: InsightResponse[] = [
    demoInsight({
      id: 'demo-exercise-mood',
      subject_id: 'demo-exercise',
      subject_label: L.exercise,
      metric: 'mood_score',
      effect_size: 0.42,
      confidence: 0.81,
      statement: t('landing.demo.stmt_exercise_mood'),
      payload: { tag_slug: 'exercise', tag_name: L.exercise },
    }),
    demoInsight({
      id: 'demo-sleep-mood',
      subject_id: 'demo-poor-sleep',
      subject_label: L.poorSleep,
      metric: 'mood_score',
      effect_size: -0.31,
      confidence: 0.68,
      statement: t('landing.demo.stmt_sleep_mood'),
      payload: { tag_slug: 'poor-sleep', tag_name: L.poorSleep },
    }),
    demoInsight({
      id: 'demo-coffee-energy',
      subject_id: 'demo-coffee',
      subject_label: L.coffee,
      metric: 'energy',
      effect_size: 0.24,
      confidence: 0.55,
      statement: t('landing.demo.stmt_coffee_energy'),
      payload: { tag_slug: 'coffee', tag_name: L.coffee },
    }),
  ];

  // Lag heatmap (#488): needs payload.method === 'lag' with ≥ 2 lag_profile
  // points; self-hides below two rows. Targets use core-metric keys so the
  // component localizes them; feature names are shown verbatim, so localize.
  const lagInsights: InsightResponse[] = [
    demoInsight({
      id: 'demo-lag-sleep-mood',
      insight_type: 'lag',
      subject_id: 'demo-poor-sleep',
      subject_label: L.poorSleep,
      metric: 'mood_score',
      effect_size: 0.62,
      confidence: 0.74,
      statement: t('landing.demo.stmt_lag_sleep_mood'),
      payload: {
        method: 'lag',
        lag_days: 2,
        feature: { name: L.poorSleep, key: 'poor-sleep', kind: 'tag' },
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
      subject_label: L.exercise,
      metric: 'energy',
      effect_size: 0.55,
      confidence: 0.7,
      statement: t('landing.demo.stmt_lag_exercise_energy'),
      payload: {
        method: 'lag',
        lag_days: 1,
        feature: { name: L.exercise, key: 'exercise', kind: 'tag' },
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

  // Weekday overview (A3): weekday_summary index 0 = Monday; Friday high,
  // Saturday low so both best/worst highlights fire.
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
        label: L.homeOffice,
        count: 6,
        share: 0.7,
      },
    },
    { weekday: 3, entry_count: 9, mood_avg: 3.5, top_signal: null },
    {
      weekday: 4,
      entry_count: 9,
      mood_avg: 4.2,
      top_signal: { kind: 'tag', id: 'demo-exercise', label: L.exercise, count: 7, share: 0.78 },
    },
    {
      weekday: 5,
      entry_count: 8,
      mood_avg: 3.1,
      top_signal: { kind: 'tag', id: 'demo-poor-sleep', label: L.poorSleep, count: 5, share: 0.63 },
    },
    { weekday: 6, entry_count: 8, mood_avg: 3.3, top_signal: null },
  ];

  const weekdayInsight: InsightResponse = demoInsight({
    id: 'demo-weekday-pattern',
    insight_type: 'weekday_pattern',
    subject_type: 'weekday',
    subject_id: 'demo-friday',
    subject_label: L.friday,
    metric: 'mood_score',
    effect_size: 0.44,
    confidence: 0.62,
    statement: t('landing.demo.stmt_weekday_friday'),
    payload: {
      weekday: 4,
      weekday_mood_avgs: { '0': 3.4, '1': 3.6, '2': 3.9, '3': 3.5, '4': 4.2, '5': 3.1, '6': 3.3 },
    },
  });

  // Co-occurrence heatmap: four tags so the grid fills the narrow frame
  // without horizontal overflow (#546) with every off-diagonal cell valued.
  const cooccurrence: TagCooccurrenceResponse = {
    range: '90d',
    start_date: '2026-04-20',
    end_date: '2026-07-19',
    min_count: 2,
    pairs: [
      {
        tag_a: cooRef('demo-poor-sleep', 'poor-sleep', L.poorSleep),
        tag_b: cooRef('demo-low-energy', 'low-energy', L.lowEnergy),
        count: 9,
        pct_of_a: 75,
        pct_of_b: 64,
      },
      {
        tag_a: cooRef('demo-poor-sleep', 'poor-sleep', L.poorSleep),
        tag_b: cooRef('demo-headache', 'headache', L.headache),
        count: 6,
        pct_of_a: 50,
        pct_of_b: 60,
      },
      {
        tag_a: cooRef('demo-poor-sleep', 'poor-sleep', L.poorSleep),
        tag_b: cooRef('demo-exercise', 'exercise', L.exercise),
        count: 2,
        pct_of_a: 17,
        pct_of_b: 18,
      },
      {
        tag_a: cooRef('demo-low-energy', 'low-energy', L.lowEnergy),
        tag_b: cooRef('demo-headache', 'headache', L.headache),
        count: 5,
        pct_of_a: 42,
        pct_of_b: 50,
      },
      {
        tag_a: cooRef('demo-low-energy', 'low-energy', L.lowEnergy),
        tag_b: cooRef('demo-exercise', 'exercise', L.exercise),
        count: 3,
        pct_of_a: 25,
        pct_of_b: 27,
      },
      {
        tag_a: cooRef('demo-headache', 'headache', L.headache),
        tag_b: cooRef('demo-exercise', 'exercise', L.exercise),
        count: 2,
        pct_of_a: 20,
        pct_of_b: 18,
      },
    ],
  };

  return {
    tagClusters,
    timeseriesPoints: landingTimeseriesPoints,
    stripPoints: landingStripPoints,
    stripAxisDates: landingStripAxisDates,
    insights,
    featuredInsight: insights[0],
    lagInsights,
    maturity: landingMaturity,
    weekdaySummary,
    weekdayInsight,
    cooccurrence,
  };
}
