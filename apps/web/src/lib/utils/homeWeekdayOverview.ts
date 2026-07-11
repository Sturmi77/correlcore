import type { InsightResponse } from '$lib/api/insights';

export const WEEKDAY_KEYS = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'] as const;
export type WeekdayKey = (typeof WEEKDAY_KEYS)[number];

export type WeekdayOverviewCell = {
  weekday: WeekdayKey;
  weekdayIndex: number;
  moodAvg: number | null;
  findingLabel: string | null;
  findingType: 'mood' | 'tag' | 'symptom' | 'context' | null;
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
  insights: readonly InsightResponse[]
): WeekdayOverviewCell[] {
  const weekdayInsight = insights.find((insight) => insight.insight_type === 'weekday_pattern');
  const moodAvgs = numericPayload(weekdayInsight?.payload?.weekday_mood_avgs);

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

  return WEEKDAY_KEYS.map((weekday, weekdayIndex) => ({
    weekday,
    weekdayIndex,
    moodAvg: moodAvgs[String(weekdayIndex)] ?? null,
    findingLabel: findingByDay.get(weekdayIndex)?.label ?? null,
    findingType: findingByDay.get(weekdayIndex)?.type ?? null,
  }));
}

export function hasWeekdayOverviewContent(cells: readonly WeekdayOverviewCell[]): boolean {
  return cells.some((cell) => cell.moodAvg !== null || cell.findingLabel !== null);
}
