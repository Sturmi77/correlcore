import type { DashboardSummaryResponse } from '$lib/api/dashboard';
import type { EntryResponse } from '$lib/api/entries';
import type { HabitStatsResponse } from '$lib/api/habits';
import type {
  InsightMaturity,
  InsightResponse,
  SymptomTagCooccurrenceResponse,
  TagClustersResponse,
  TagCooccurrenceRange,
  TagCooccurrenceResponse,
} from '$lib/api/insights';
import type {
  EntryStreakResponse,
  SymptomHeatmapResponse,
  TagHeatmapResponse,
  TimeseriesResponse,
} from '$lib/api/stats';
import type { TagResponse } from '$lib/api/tags';
import type { UserPreferencesResponse } from '$lib/api/preferences';
import { localIsoDate, shiftIsoDate } from '$lib/utils/streak';
import {
  PERSONA_SYMPTOMS,
  PERSONA_TAGS,
  daysToEntries,
  generateOfficeSportDays,
  pythonWeekday,
  symptomHeatmapFromDays,
  symptomsByEntryId,
  tagHeatmapFromDays,
  tagPairsFromDays,
  tagsByEntryId,
  type PersonaDay,
  type PersonaTagRef,
} from '$lib/dev/personaDataset';

export type DevPhasePresetId = 'collecting' | 'early_patterns' | 'provisional' | 'robust';

export interface DevPhaseStateLike {
  presetId: DevPhasePresetId;
  entryCount: number;
  onboardingCompleted: boolean;
}

export interface DevPhasePresetMeta {
  id: DevPhasePresetId;
  defaultEntryCount: number;
  coverageKey: string;
}

export interface DevPhaseFixture {
  presetId: DevPhasePresetId;
  entryCount: number;
  maturity: InsightMaturity;
  insights: InsightResponse[];
  entries: EntryResponse[];
  dashboard: DashboardSummaryResponse;
  preferences: UserPreferencesResponse;
  timeseries: TimeseriesResponse;
  tagHeatmap: TagHeatmapResponse;
  symptomHeatmap: SymptomHeatmapResponse;
  streak: EntryStreakResponse;
  habitStats: HabitStatsResponse[];
  habitTags: TagResponse[];
  tagCooccurrenceByRange: Record<TagCooccurrenceRange, TagCooccurrenceResponse>;
  symptomTagCooccurrenceByRange: Record<TagCooccurrenceRange, SymptomTagCooccurrenceResponse>;
  tagClusters: TagClustersResponse;
  tagsByEntryId: Record<string, string[]>;
  symptomsByEntryId: Record<string, { name: string; intensity: number }[]>;
}

const today = localIsoDate(new Date());
const userId = 'mock-user';
const generatedAt = `${today}T09:00:00Z`;

export const DEV_PHASE_PRESETS: Record<DevPhasePresetId, DevPhasePresetMeta> = {
  collecting: {
    id: 'collecting',
    defaultEntryCount: 3,
    coverageKey: 'settings.developer.coverage.collecting',
  },
  early_patterns: {
    id: 'early_patterns',
    defaultEntryCount: 9,
    coverageKey: 'settings.developer.coverage.early_patterns',
  },
  provisional: {
    id: 'provisional',
    defaultEntryCount: 21,
    coverageKey: 'settings.developer.coverage.provisional',
  },
  robust: {
    id: 'robust',
    defaultEntryCount: 42,
    coverageKey: 'settings.developer.coverage.robust',
  },
};

const phaseConfig: Record<
  DevPhasePresetId,
  Pick<InsightMaturity, 'phase_index' | 'next_phase_at' | 'next_phase_label' | 'user_message_key'>
> = {
  collecting: {
    phase_index: 1,
    next_phase_at: 7,
    next_phase_label: 'First Patterns',
    user_message_key: 'maturity.collecting.description',
  },
  early_patterns: {
    phase_index: 2,
    next_phase_at: 14,
    next_phase_label: 'Provisional Insights',
    user_message_key: 'maturity.early_patterns.description',
  },
  provisional: {
    phase_index: 3,
    next_phase_at: 30,
    next_phase_label: 'Robust Insights',
    user_message_key: 'maturity.provisional.description',
  },
  robust: {
    phase_index: 4,
    next_phase_at: null,
    next_phase_label: null,
    user_message_key: 'maturity.robust.description',
  },
};

const tagRefs = {
  focus: PERSONA_TAGS.focus,
  walk: PERSONA_TAGS.walk,
  coffee: PERSONA_TAGS.caffeine,
  read: PERSONA_TAGS.reading,
  meetings: PERSONA_TAGS.meetings,
  alcohol: PERSONA_TAGS.alcohol,
} as const;

const symptomRefs = {
  fatigue: PERSONA_SYMPTOMS.fatigue,
  headache: PERSONA_SYMPTOMS.headache,
} as const;

export function devMaturityFromPreset(
  presetId: DevPhasePresetId,
  entryCount = DEV_PHASE_PRESETS[presetId].defaultEntryCount
): InsightMaturity {
  const config = phaseConfig[presetId];
  return {
    phase: presetId,
    phase_index: config.phase_index,
    current_entries: entryCount,
    next_phase_at: config.next_phase_at,
    next_phase_label: config.next_phase_label,
    entries_until_next:
      config.next_phase_at === null ? null : Math.max(0, config.next_phase_at - entryCount),
    user_message_key: config.user_message_key,
  };
}

function makeEntries(days: PersonaDay[]): EntryResponse[] {
  return daysToEntries(days, userId);
}

function makeTimeseries(entries: EntryResponse[]): TimeseriesResponse {
  return {
    range: 'week',
    points: entries
      .slice(0, 14)
      .reverse()
      .map((entry) => ({
        period_start: entry.entry_date,
        period_end: entry.entry_date,
        entry_count: 1,
        mood_avg: entry.mood_score,
        energy_avg: entry.energy,
        stress_avg: entry.stress,
        sleep_quality_avg: entry.sleep_quality ?? null,
      })),
  };
}

function makeTagHeatmap(days: PersonaDay[], density: number): TagHeatmapResponse {
  return tagHeatmapFromDays(days, density);
}

function makeSymptomHeatmap(days: PersonaDay[], density: number): SymptomHeatmapResponse {
  return symptomHeatmapFromDays(days, density);
}

function makeStreak(entries: EntryResponse[], entryCount: number): EntryStreakResponse {
  return {
    current_streak: Math.min(entryCount, 6),
    longest_streak: Math.min(entryCount, 12),
    total_entry_days: entryCount,
    last_entry_date: entries[0]?.entry_date ?? null,
    as_of: today,
  };
}

function makeHabitTags(enabled: boolean): TagResponse[] {
  if (!enabled) return [];
  return [
    {
      id: tagRefs.walk.tag_id,
      user_id: userId,
      slug: tagRefs.walk.slug,
      name: tagRefs.walk.name,
      category: 'health',
      icon: 'footprints',
      color: null,
      is_default: false,
      is_hidden: false,
      include_in_analytics: true,
      habit_type: 'build',
      target_frequency: 4,
      created_at: generatedAt,
      updated_at: generatedAt,
    },
    {
      id: tagRefs.alcohol.tag_id,
      user_id: userId,
      slug: tagRefs.alcohol.slug,
      name: tagRefs.alcohol.name,
      category: 'consumption',
      icon: 'wine',
      color: null,
      is_default: false,
      is_hidden: false,
      include_in_analytics: true,
      habit_type: 'reduce',
      target_frequency: 2,
      created_at: generatedAt,
      updated_at: generatedAt,
    },
  ];
}

function makeHabitStats(entries: EntryResponse[], enabled: boolean): HabitStatsResponse[] {
  if (!enabled) return [];
  return [
    {
      tag_id: tagRefs.walk.tag_id,
      habit_type: 'build',
      target_frequency: 4,
      window: 28,
      start_date: shiftIsoDate(today, -27),
      end_date: today,
      days_tracked: Math.min(entries.length, 12),
      days_total: 28,
      target_days: 16,
      adherence_rate: 75,
      previous_adherence_rate: 62.5,
      adherence_delta: 12.5,
      trend_direction: 'up',
      correlation_score: entries.length >= 30 ? 0.48 : null,
      correlation_metric: entries.length >= 30 ? 'mood' : null,
    },
    {
      tag_id: tagRefs.alcohol.tag_id,
      habit_type: 'reduce',
      target_frequency: 2,
      window: 28,
      start_date: shiftIsoDate(today, -27),
      end_date: today,
      days_tracked: Math.min(entries.length, 14),
      days_total: 28,
      target_days: 20,
      adherence_rate: 100,
      previous_adherence_rate: 100,
      adherence_delta: 0,
      trend_direction: 'flat',
      correlation_score: null,
      correlation_metric: null,
    },
  ];
}

function makeInsight(
  presetId: DevPhasePresetId,
  id: string,
  overrides: Partial<InsightResponse>
): InsightResponse {
  return {
    id,
    user_id: userId,
    insight_type: 'pointbiserial',
    tier: presetId === 'robust' ? 'developing' : 'preliminary',
    metric: 'mood',
    subject_type: 'tag',
    subject_id: tagRefs.focus.tag_id,
    subject_label: tagRefs.focus.name,
    effect_size: 0.32,
    confidence: 0.5,
    sample_n: DEV_PHASE_PRESETS[presetId].defaultEntryCount,
    statement: null,
    flags: { causal_claim: false, mock: true, phase: presetId },
    payload: {},
    generated_for_date: today,
    generated_at: generatedAt,
    created_at: generatedAt,
    updated_at: generatedAt,
    ...overrides,
  };
}

function makeWeekdayPatternInsight(
  presetId: DevPhasePresetId,
  entryCount: number,
  id: string
): InsightResponse {
  return makeInsight(presetId, id, {
    insight_type: 'weekday_pattern',
    tier: presetId === 'robust' ? 'developing' : 'preliminary',
    metric: 'mood_score',
    subject_type: 'weekday',
    subject_id: null,
    subject_label: 'Friday',
    effect_size: 0.24,
    confidence: presetId === 'robust' ? 0.52 : 0.38,
    sample_n: entryCount,
    statement: 'Mood is often higher near the end of the week.',
    payload: {
      weekday: 4,
      weekday_mood_avg: 3.8,
      weekday_mood_avgs: {
        '0': 3.1,
        '1': 3.0,
        '2': 3.2,
        '3': 3.1,
        '4': 3.8,
        '5': 3.3,
        '6': 3.0,
      },
      overall_mood_avg: 3.2,
    },
  });
}

function makeInsights(presetId: DevPhasePresetId, entryCount: number): InsightResponse[] {
  if (presetId === 'collecting') return [];
  if (presetId === 'early_patterns') {
    return [
      makeInsight(presetId, 'mock-insight-first-pattern', {
        insight_type: 'weekday_pattern',
        tier: 'early',
        metric: 'mood_score',
        subject_type: 'weekday',
        subject_id: null,
        subject_label: 'Friday',
        effect_size: 0.24,
        confidence: 0.38,
        sample_n: entryCount,
        statement: 'A first hint that mood is often higher near the end of the week.',
        // weekday_mood_avgs drives HomeWeekdayOverview's per-day bars — without
        // it hasWeekdayOverviewContent() is false and the section renders
        // nothing, even though this insight's statement is explicitly about a
        // weekday pattern. Index 4 = Friday, matching subject_label above.
        payload: {
          weekday: 4,
          weekday_mood_avg: 3.8,
          weekday_mood_avgs: {
            '0': 3.1,
            '1': 3.0,
            '2': 3.2,
            '3': 3.1,
            '4': 3.8,
            '5': 3.3,
            '6': 3.0,
          },
          overall_mood_avg: 3.2,
        },
      }),
    ];
  }
  const common = [
    makeInsight(presetId, 'mock-insight-energy-mood', {
      insight_type: 'spearman',
      tier: presetId === 'robust' ? 'developing' : 'preliminary',
      metric: 'mood',
      subject_type: 'metric',
      subject_id: 'energy',
      subject_label: 'Energy',
      effect_size: presetId === 'robust' ? 0.58 : 0.42,
      confidence: presetId === 'robust' ? 0.72 : 0.56,
      sample_n: entryCount,
      statement:
        presetId === 'robust'
          ? 'Mood and energy tend to move together across recent entries.'
          : 'An early correlation between mood and energy; more entries may revise it.',
    }),
    makeInsight(presetId, 'mock-insight-tag-walk', {
      insight_type: 'pointbiserial',
      tier: 'preliminary',
      metric: 'mood',
      subject_type: 'tag',
      subject_id: tagRefs.walk.tag_id,
      subject_label: tagRefs.walk.name,
      effect_size: presetId === 'robust' ? 0.36 : 0.3,
      confidence: presetId === 'robust' ? 0.54 : 0.46,
      sample_n: entryCount,
      statement: 'Days with a walk tend to line up with slightly higher mood.',
    }),
    makeWeekdayPatternInsight(presetId, entryCount, `mock-insight-weekday-${presetId}`),
  ];
  if (presetId === 'provisional') return common;
  return [
    ...common,
    makeInsight(presetId, 'mock-insight-symptom-mood', {
      insight_type: 'symptom_mood_association',
      tier: 'developing',
      metric: 'mood_score',
      subject_type: 'symptom',
      subject_id: symptomRefs.headache.symptom_id,
      subject_label: symptomRefs.headache.name,
      effect_size: -0.42,
      confidence: 0.64,
      sample_n: entryCount,
      statement: 'Days with a headache tend to line up with lower mood.',
      flags: { causal_claim: false, mock: true, method: 'pointbiserial', phase: presetId },
      payload: {
        kind: 'symptom_mood_association',
        symptom_name: symptomRefs.headache.name,
        symptom_slug: symptomRefs.headache.slug,
        symptom_n: 9,
        p_value_corrected: 0.04,
      },
    }),
    makeInsight(presetId, 'mock-insight-symptom-tag', {
      insight_type: 'symptom_tag_cooccurrence',
      tier: 'developing',
      metric: 'symptom_tag_cooccurrence',
      subject_type: 'symptom_tag',
      subject_id: null,
      subject_label: 'Headache + Meetings',
      effect_size: 0.38,
      confidence: 0.58,
      sample_n: entryCount,
      statement:
        'Headache days appear together with Meetings more often than their separate frequencies would suggest.',
      flags: { causal_claim: false, mock: true, method: 'fisher_exact_lift', phase: presetId },
      payload: {
        kind: 'symptom_tag_cooccurrence',
        symptom_name: symptomRefs.headache.name,
        symptom_slug: symptomRefs.headache.slug,
        tag_name: tagRefs.meetings.name,
        tag_slug: tagRefs.meetings.slug,
        lift: 2.1,
        co_count: 7,
        p_value_corrected: 0.03,
      },
    }),
    makeInsight(presetId, 'mock-insight-symptom-cluster-lasso', {
      insight_type: 'symptom_cluster',
      tier: 'developing',
      metric: 'mood_score',
      subject_type: 'metric',
      subject_id: null,
      subject_label: 'mood_score',
      effect_size: 0.44,
      confidence: 0.61,
      sample_n: entryCount,
      statement: 'Several tracked signals line up with mood, led by walks and meetings.',
      flags: { causal_claim: false, mock: true, method: 'lasso', phase: presetId },
      payload: {
        method: 'lasso',
        target: 'mood_score',
        features: [
          { kind: 'tag', key: 'tag:walk', name: 'Walk', coefficient: 0.31 },
          { kind: 'tag', key: 'tag:meeting_heavy', name: 'Meetings', coefficient: -0.22 },
        ],
      },
    }),
    makeInsight(presetId, 'mock-insight-symptom-cluster-lag', {
      insight_type: 'symptom_cluster',
      tier: 'developing',
      metric: 'mood_score',
      subject_type: 'metric',
      subject_id: null,
      subject_label: 'mood_score',
      effect_size: 0.29,
      confidence: 0.55,
      sample_n: entryCount,
      statement: 'A walk one day earlier tends to line up with higher mood.',
      flags: { causal_claim: false, mock: true, method: 'lag', phase: presetId },
      payload: {
        method: 'lag',
        target: { kind: 'metric', key: 'mood_score', name: 'Mood' },
        feature: { kind: 'tag', key: 'tag:walk', name: 'Walk' },
        lag_days: 1,
      },
    }),
    makeInsight(presetId, 'mock-insight-work-context', {
      insight_type: 'work_context_pattern',
      tier: 'developing',
      metric: 'mood_score',
      subject_type: 'work_context',
      subject_id: null,
      subject_label: 'Office',
      effect_size: 0.18,
      confidence: 0.48,
      sample_n: entryCount,
      statement: 'Home-office days show a slightly different mood average than office days.',
      payload: { work_context: 'office' },
    }),
    makeInsight(presetId, 'mock-insight-weekday-context', {
      insight_type: 'weekday_context_pattern',
      tier: 'developing',
      metric: 'mood_score',
      subject_type: 'weekday',
      subject_id: null,
      subject_label: 'Monday',
      effect_size: 0.15,
      confidence: 0.42,
      sample_n: entryCount,
      statement: 'Monday office days sit a little apart from the rest of the week.',
      payload: { weekday: 0, work_context: 'office' },
    }),
  ];
}

function makePairResponse(
  range: TagCooccurrenceRange,
  startOffset: number,
  days: PersonaDay[],
  enabled: boolean
): TagCooccurrenceResponse {
  return {
    range,
    start_date: shiftIsoDate(today, startOffset),
    end_date: today,
    min_count: 2,
    pairs: enabled ? tagPairsFromDays(days, startOffset) : [],
  };
}

function makeTagCooccurrenceByRange(
  days: PersonaDay[],
  enabled: boolean
): Record<TagCooccurrenceRange, TagCooccurrenceResponse> {
  return {
    '7d': makePairResponse('7d', -6, days, enabled),
    '30d': makePairResponse('30d', -29, days, enabled),
    '90d': makePairResponse('90d', -89, days, enabled),
    '1y': makePairResponse('1y', -364, days, enabled),
  };
}

function makeSymptomTagCooccurrenceByRange(
  entryCount: number,
  enabled: boolean
): Record<TagCooccurrenceRange, SymptomTagCooccurrenceResponse> {
  const makeCells = (range: TagCooccurrenceRange, startOffset: number, totalCount: number) => ({
    range,
    start_date: shiftIsoDate(today, startOffset),
    end_date: today,
    min_count: 3,
    cells: enabled
      ? [
          {
            symptom: symptomRefs.headache,
            tag: tagRefs.meetings,
            phi: 0.38,
            jaccard: 0.41,
            lift: 2.1,
            co_count: Math.max(3, Math.round(totalCount / 6)),
            symptom_count: Math.max(5, Math.round(totalCount / 4)),
            tag_count: Math.max(7, Math.round(totalCount / 3)),
            total_count: totalCount,
            p_value_corrected: 0.03,
            confounder: null,
          },
          {
            symptom: symptomRefs.fatigue,
            tag: tagRefs.walk,
            phi: -0.29,
            jaccard: 0.12,
            lift: 0.5,
            co_count: 3,
            symptom_count: Math.max(5, Math.round(totalCount / 5)),
            tag_count: Math.max(7, Math.round(totalCount / 3)),
            total_count: totalCount,
            p_value_corrected: 0.08,
            confounder: null,
          },
        ]
      : [],
  });
  return {
    '7d': makeCells('7d', -6, Math.max(entryCount, 8)),
    '30d': makeCells('30d', -29, Math.max(entryCount, 18)),
    '90d': makeCells('90d', -89, Math.max(entryCount, 42)),
    '1y': makeCells('1y', -364, Math.max(entryCount + 48, 96)),
  };
}

function makeTagClusters(entryCount: number, enabled: boolean): TagClustersResponse {
  if (!enabled || entryCount < 30) {
    return {
      status: 'insufficient_data',
      entry_count: entryCount,
      active_tag_count: enabled ? 4 : 0,
      active_signal_count: enabled ? 4 : 0,
      window_days: Math.min(entryCount, 90),
      k: null,
      reason: enabled ? 'entry_count_below_30' : 'dev_phase_gate',
      cluster_kind: 'mixed',
      entries_until_robust: Math.max(0, 90 - entryCount),
      clusters: [],
    };
  }

  const clusterMaturity = entryCount >= 90 ? 'robust' : entryCount >= 45 ? 'provisional' : 'early';
  const clusterMode = entryCount >= 45 ? 'kmeans' : 'pair';

  return {
    status: 'ok',
    entry_count: entryCount,
    active_tag_count: 6,
    active_signal_count: 7,
    window_days: Math.min(entryCount, 90),
    k: clusterMode === 'kmeans' ? 3 : null,
    reason: null,
    cluster_kind: entryCount >= 90 ? 'mixed' : 'tags_only',
    cluster_maturity: clusterMaturity,
    cluster_mode: clusterMode,
    entries_until_robust: entryCount >= 90 ? null : 90 - entryCount,
    silhouette_score: clusterMode === 'kmeans' ? 0.115 : null,
    clusters: [
      {
        cluster_id: 1,
        label: tagRefs.focus.name,
        cluster_kind: 'mixed',
        strength: 0.72,
        tags: [tagRefs.focus, tagRefs.read],
        members: [
          {
            kind: 'tag',
            signal_id: tagRefs.focus.tag_id,
            slug: tagRefs.focus.slug,
            name: tagRefs.focus.name,
            category: tagRefs.focus.category,
            color: null,
          },
          {
            kind: 'tag',
            signal_id: tagRefs.read.tag_id,
            slug: tagRefs.read.slug,
            name: tagRefs.read.name,
            category: tagRefs.read.category,
            color: null,
          },
          {
            kind: 'symptom',
            signal_id: symptomRefs.headache.symptom_id,
            slug: symptomRefs.headache.slug,
            name: symptomRefs.headache.name,
            icon: symptomRefs.headache.icon,
          },
        ],
      },
      {
        cluster_id: 2,
        label: tagRefs.walk.name,
        cluster_kind: 'mixed',
        strength: 0.64,
        tags: [tagRefs.walk],
        members: [
          {
            kind: 'tag',
            signal_id: tagRefs.walk.tag_id,
            slug: tagRefs.walk.slug,
            name: tagRefs.walk.name,
            category: tagRefs.walk.category,
            color: null,
          },
        ],
      },
    ],
  };
}

function makeWorkContextSummary(
  days: PersonaDay[]
): DashboardSummaryResponse['work_context_summary'] {
  const groups = new Map<
    EntryResponse['work_context'],
    { count: number; mood: number; energy: number; stress: number }
  >();
  for (const day of days) {
    const bucket = groups.get(day.workContext) ?? { count: 0, mood: 0, energy: 0, stress: 0 };
    bucket.count += 1;
    bucket.mood += day.mood;
    bucket.energy += day.energy;
    bucket.stress += day.stress;
    groups.set(day.workContext, bucket);
  }
  return [...groups.entries()].map(([work_context, bucket]) => ({
    work_context,
    entry_count: bucket.count,
    mood_avg: Number((bucket.mood / bucket.count).toFixed(2)),
    energy_avg: Number((bucket.energy / bucket.count).toFixed(2)),
    stress_avg: Number((bucket.stress / bucket.count).toFixed(2)),
  }));
}

function makeWeekdaySummary(days: PersonaDay[]): DashboardSummaryResponse['weekday_summary'] {
  if (days.length < 7) return [];

  const byWeekday = new Map<
    number,
    {
      count: number;
      moods: number[];
      tagCounts: Map<string, { ref: PersonaTagRef; n: number }>;
    }
  >();
  for (const day of days) {
    const weekday = pythonWeekday(day.date);
    const bucket = byWeekday.get(weekday) ?? {
      count: 0,
      moods: [] as number[],
      tagCounts: new Map<string, { ref: PersonaTagRef; n: number }>(),
    };
    bucket.count += 1;
    bucket.moods.push(day.mood);
    for (const tag of day.tags) {
      const current = bucket.tagCounts.get(tag.slug) ?? { ref: tag, n: 0 };
      current.n += 1;
      bucket.tagCounts.set(tag.slug, current);
    }
    byWeekday.set(weekday, bucket);
  }

  if (byWeekday.size < 7) return [];

  return [...byWeekday.entries()]
    .sort(([left], [right]) => left - right)
    .map(([weekday, bucket]) => {
      const top = [...bucket.tagCounts.values()].sort((a, b) => b.n - a.n)[0];
      return {
        weekday,
        entry_count: bucket.count,
        mood_avg: Number(
          (bucket.moods.reduce((sum, mood) => sum + mood, 0) / bucket.moods.length).toFixed(2)
        ),
        top_signal: top
          ? {
              kind: 'tag' as const,
              id: top.ref.tag_id,
              label: top.ref.name,
              count: top.n,
              share: Number((top.n / bucket.count).toFixed(2)),
            }
          : null,
      };
    });
}

function makePreferences(
  onboardingCompleted: boolean,
  presetId: DevPhasePresetId
): UserPreferencesResponse {
  return {
    user_id: userId,
    analytics_enabled: true,
    digest_enabled: true,
    onboarding_retro_completed: onboardingCompleted,
    onboarding_profile_completed: onboardingCompleted,
    // Dev fixtures skip the one-time intro so phase QA stays unblocked.
    onboarding_maturity_intro_seen: true,
    cycle_tracking_enabled: true,
    dismissed_insight_keys: [],
    reached_milestone_keys: presetId === 'collecting' ? [] : [`maturity_phase_${presetId}`],
    last_seen_insight_at: null,
    home_sections: null,
    created_at: generatedAt,
    updated_at: generatedAt,
  };
}

export function getDevPhaseFixture(state: DevPhaseStateLike): DevPhaseFixture {
  const preset = DEV_PHASE_PRESETS[state.presetId];
  const rawEntryCount = Number.isFinite(state.entryCount)
    ? state.entryCount
    : preset.defaultEntryCount;
  const entryCount = Math.max(0, Math.min(200, rawEntryCount));
  const days = generateOfficeSportDays(today, entryCount);
  const entries = makeEntries(days);
  const insightEnabled = state.presetId !== 'collecting';
  const analyticsEnabled = state.presetId === 'provisional' || state.presetId === 'robust';
  const robustEnabled = state.presetId === 'robust';
  return {
    presetId: state.presetId,
    entryCount,
    maturity: devMaturityFromPreset(state.presetId, entryCount),
    insights: makeInsights(state.presetId, entryCount),
    entries,
    dashboard: {
      entry_count: entryCount,
      insight_tier:
        state.presetId === 'collecting'
          ? 'none'
          : state.presetId === 'robust'
            ? 'developing'
            : state.presetId === 'provisional'
              ? 'preliminary'
              : 'early',
      confidence_score:
        state.presetId === 'robust' ? 0.66 : state.presetId === 'provisional' ? 0.48 : 0.22,
      work_context_summary: makeWorkContextSummary(days),
      weekday_summary: makeWeekdaySummary(days),
    },
    preferences: makePreferences(state.onboardingCompleted, state.presetId),
    timeseries: makeTimeseries(entries),
    tagHeatmap: makeTagHeatmap(days, insightEnabled ? (robustEnabled ? 7 : 4) : 0),
    symptomHeatmap: makeSymptomHeatmap(days, analyticsEnabled ? (robustEnabled ? 7 : 4) : 0),
    streak: makeStreak(entries, entryCount),
    habitStats: makeHabitStats(entries, insightEnabled),
    habitTags: makeHabitTags(insightEnabled),
    tagCooccurrenceByRange: makeTagCooccurrenceByRange(days, analyticsEnabled),
    symptomTagCooccurrenceByRange: makeSymptomTagCooccurrenceByRange(entryCount, robustEnabled),
    tagClusters: makeTagClusters(entryCount, robustEnabled),
    tagsByEntryId: tagsByEntryId(days),
    symptomsByEntryId: symptomsByEntryId(days),
  };
}

export const defaultDevPhaseFixture = getDevPhaseFixture({
  presetId: 'robust',
  entryCount: DEV_PHASE_PRESETS.robust.defaultEntryCount,
  onboardingCompleted: true,
});
