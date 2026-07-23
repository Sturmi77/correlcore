import type { InsightResponse } from '$lib/api/insights';
import type { WeekdaySummaryItem } from '$lib/api/dashboard';

export const WEEKDAY_KEYS = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'] as const;
export type WeekdayKey = (typeof WEEKDAY_KEYS)[number];

export type WeekdayOverviewCell = {
  weekday: WeekdayKey;
  weekdayIndex: number;
  moodAvg: number | null;
  findingLabel: string | null;
  findingType: 'mood' | 'tag' | 'symptom' | 'context' | null;
  /**
   * Where the finding came from (#487).
   *
   * `confounder` is the rarer and stronger statement — an association that
   * looked real but dissolves once weekday effects are adjusted for. It always
   * wins over `top_signal`, which is purely descriptive ("this happens most
   * often on this day") and only fills days that have no confounder.
   */
  findingSource: 'confounder' | 'top_signal' | null;
  /**
   * i18n key when the label is an application enum rather than user data.
   *
   * Tag and symptom labels are user-supplied and shown verbatim; `work_context`
   * is a backend enum, so rendering it raw would surface `homeoffice` instead
   * of "Homeoffice" (#487 review).
   */
  findingLabelKey: string | null;
};

const TOP_SIGNAL_KIND_TO_FINDING_TYPE: Record<
  NonNullable<WeekdaySummaryItem['top_signal']>['kind'],
  WeekdayOverviewCell['findingType']
> = {
  tag: 'tag',
  symptom: 'symptom',
  work_context: 'context',
};

function numericPayload(value: unknown): Record<string, number> {
  if (!value || typeof value !== 'object') return {};
  return Object.fromEntries(
    Object.entries(value as Record<string, unknown>)
      .filter(([, v]) => typeof v === 'number' && Number.isFinite(v))
      .map(([k, v]) => [k, v as number])
  );
}

function weekdayIndexFromInsight(insight: InsightResponse): number | null {
  const payloadWeekday = insight.payload?.weekday;
  if (typeof payloadWeekday === 'number' && payloadWeekday >= 0 && payloadWeekday <= 6) {
    return payloadWeekday;
  }
  const label = insight.subject_label?.toLowerCase() ?? '';
  const map: Record<string, number> = {
    monday: 0,
    montag: 0,
    mo: 0,
    tuesday: 1,
    dienstag: 1,
    di: 1,
    wednesday: 2,
    mittwoch: 2,
    mi: 2,
    thursday: 3,
    donnerstag: 3,
    do: 3,
    friday: 4,
    freitag: 4,
    fr: 4,
    saturday: 5,
    samstag: 5,
    sa: 5,
    sunday: 6,
    sonntag: 6,
    so: 6,
  };
  for (const [key, index] of Object.entries(map)) {
    if (label.includes(key)) return index;
  }
  return null;
}

function isWeekdayConfounded(insight: InsightResponse): boolean {
  return (
    insight.flags?.weekday_confounded === true ||
    insight.flags?.calendar_context_confounded === true
  );
}

function findingLabelFor(insight: InsightResponse): string {
  return insight.subject_label ?? insight.metric ?? insight.insight_type;
}

function findingTypeFor(insight: InsightResponse): WeekdayOverviewCell['findingType'] {
  if (insight.insight_type === 'weekday_pattern') return 'mood';
  if (insight.subject_type === 'symptom') return 'symptom';
  if (insight.subject_type === 'tag') return 'tag';
  if (insight.subject_type === 'weekday' || insight.subject_type === 'work_context') {
    return 'context';
  }
  return 'context';
}

export function buildWeekdayOverviewCells(
  insights: readonly InsightResponse[],
  weekdaySummary: readonly WeekdaySummaryItem[] = []
): WeekdayOverviewCell[] {
  const summaryMoods = new Map(
    weekdaySummary
      .filter((item) => item.mood_avg !== null)
      .map((item) => [item.weekday, item.mood_avg as number])
  );

  const weekdayInsight = insights.find((insight) => insight.insight_type === 'weekday_pattern');
  const insightMoods = numericPayload(weekdayInsight?.payload?.weekday_mood_avgs);

  const findingByDay = new Map<
    number,
    { label: string; type: WeekdayOverviewCell['findingType'] }
  >();

  for (const insight of insights) {
    if (insight.insight_type === 'weekday_pattern') continue;
    if (!isWeekdayConfounded(insight)) continue;
    const dayIndex = weekdayIndexFromInsight(insight);
    if (dayIndex === null || findingByDay.has(dayIndex)) continue;
    findingByDay.set(dayIndex, {
      label: findingLabelFor(insight),
      type: findingTypeFor(insight),
    });
  }

  // Top signals only fill days a confounder did not claim (#487).
  const topSignalByDay = new Map(
    weekdaySummary.filter((item) => item.top_signal).map((item) => [item.weekday, item.top_signal!])
  );

  return WEEKDAY_KEYS.map((weekday, weekdayIndex) => {
    const confounder = findingByDay.get(weekdayIndex);
    const topSignal = confounder ? undefined : topSignalByDay.get(weekdayIndex);
    return {
      weekday,
      weekdayIndex,
      moodAvg: summaryMoods.get(weekdayIndex) ?? insightMoods[String(weekdayIndex)] ?? null,
      findingLabel: confounder?.label ?? topSignal?.label ?? null,
      findingType:
        confounder?.type ?? (topSignal ? TOP_SIGNAL_KIND_TO_FINDING_TYPE[topSignal.kind] : null),
      findingSource: confounder ? 'confounder' : topSignal ? 'top_signal' : null,
      findingLabelKey:
        !confounder && topSignal?.kind === 'work_context'
          ? `entry.work_context.${topSignal.label}`
          : null,
    };
  });
}

export function hasWeekdayOverviewContent(cells: readonly WeekdayOverviewCell[]): boolean {
  return cells.some((cell) => cell.moodAvg !== null || cell.findingLabel !== null);
}

/**
 * Pick the most recently generated `weekday_pattern` insight.
 *
 * `/insights/latest`'s per-subject dedup keys weekday_pattern rows by their
 * weekday *label* (e.g. "Friday" vs "Wednesday" — subject_id is always null
 * for this type), not as a single subject. If a user's strongest weekday
 * changes between generation runs, an older row for the previous label can
 * coexist with a newer row for the current one instead of being superseded.
 * Insight-ranking order (confidence × |effect_size|) doesn't reflect this —
 * an older high-scoring weekday pattern can rank above a newer, lower-scoring
 * one. Select by `generated_for_date` explicitly instead of trusting rank
 * order, so Home always shows the current pattern, not a stale one.
 */
export function selectNewestWeekdayPattern(
  insights: readonly InsightResponse[]
): InsightResponse | null {
  const candidates = insights.filter((insight) => insight.insight_type === 'weekday_pattern');
  if (candidates.length === 0) return null;
  return candidates.reduce((newest, candidate) =>
    candidate.generated_for_date.localeCompare(newest.generated_for_date) > 0 ? candidate : newest
  );
}
