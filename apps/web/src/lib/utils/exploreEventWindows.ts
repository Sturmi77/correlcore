import type { EntryResponse } from '$lib/api/entries';
import type { InsightResponse } from '$lib/api/insights';
import type { SymptomHeatmapResponse, TagHeatmapResponse } from '$lib/api/stats';
import type { EventWindow } from '$lib/components/trends/EventAlignedSmallMultiplesSheet.svelte';
import type { MetricKey } from '$lib/utils/charts';

/** #488: lag insights align on the feature (antecedent), not the subject. */
export function lagFeatureKind(insight: InsightResponse): 'tag' | 'symptom' | null {
  const payload = insight.payload as Record<string, unknown> | undefined;
  if (!payload || payload.method !== 'lag') return null;
  const feature = payload.feature as Record<string, unknown> | undefined;
  const kind = feature?.kind;
  return kind === 'tag' || kind === 'symptom' ? kind : null;
}

/**
 * ADR-0035 §6: tag/symptom subjects have per-day presence windows. #488 aligns
 * lag insights on the feature instead, so their eligibility depends *only* on
 * whether the feature is a tag/symptom — a metric feature has no presence dates
 * and the backend returns 422, so the outcome subject must not re-enable it.
 */
export function isExploreEventsSubject(insight: InsightResponse): boolean {
  const payload = insight.payload as Record<string, unknown> | undefined;
  if (payload?.method === 'lag') {
    return lagFeatureKind(insight) !== null;
  }
  return insight.subject_type === 'tag' || insight.subject_type === 'symptom';
}

export function insightMetricToChartKey(metric: string | null | undefined): MetricKey {
  if (metric === 'energy' || metric === 'energy_avg') return 'energy_avg';
  if (metric === 'stress' || metric === 'stress_avg') return 'stress_avg';
  if (metric === 'sleep_quality' || metric === 'sleep_quality_avg') return 'sleep_quality_avg';
  return 'mood_avg';
}

export function datesToEventWindows(
  dates: readonly string[],
  label?: string | null
): EventWindow[] {
  const unique = [...new Set(dates)].sort();
  return unique.map((onset) => ({
    onset,
    label: label ?? undefined,
  }));
}

export async function collectTagPresenceDates(
  entries: readonly EntryResponse[],
  tagId: string,
  listTagsForEntry: (entryId: string) => Promise<{ id: string }[]>
): Promise<string[]> {
  const dates: string[] = [];
  for (const entry of entries) {
    const tags = await listTagsForEntry(entry.id);
    if (tags.some((tag) => tag.id === tagId)) {
      dates.push(entry.entry_date);
    }
  }
  return dates;
}

export async function collectSymptomPresenceDates(
  entries: readonly EntryResponse[],
  symptomId: string,
  listSymptomsForEntry: (entryId: string) => Promise<{ symptom_id: string }[]>
): Promise<string[]> {
  const dates: string[] = [];
  for (const entry of entries) {
    const symptoms = await listSymptomsForEntry(entry.id);
    if (symptoms.some((symptom) => symptom.symptom_id === symptomId)) {
      dates.push(entry.entry_date);
    }
  }
  return dates;
}

export async function buildExploreEventWindows(
  insight: InsightResponse,
  entries: readonly EntryResponse[],
  listTagsForEntry: (entryId: string) => Promise<{ id: string }[]>,
  listSymptomsForEntry: (entryId: string) => Promise<{ symptom_id: string }[]>
): Promise<EventWindow[]> {
  if (!isExploreEventsSubject(insight) || !insight.subject_id) return [];

  if (insight.subject_type === 'tag') {
    const dates = await collectTagPresenceDates(entries, insight.subject_id, listTagsForEntry);
    return datesToEventWindows(dates, insight.subject_label);
  }

  const dates = await collectSymptomPresenceDates(
    entries,
    insight.subject_id,
    listSymptomsForEntry
  );
  return datesToEventWindows(dates, insight.subject_label);
}

/** Dev fixtures: derive onset dates from pre-built heatmap payloads. */
export function devEventWindowsFromHeatmaps(
  insight: InsightResponse,
  tagHeatmap: TagHeatmapResponse,
  symptomHeatmap: SymptomHeatmapResponse
): EventWindow[] {
  if (!isExploreEventsSubject(insight) || !insight.subject_id) return [];

  if (insight.subject_type === 'tag') {
    const tag = tagHeatmap.tags.find((row) => row.tag_id === insight.subject_id);
    if (!tag) return [];
    const dates = tag.days.filter((day) => day.count > 0).map((day) => day.date);
    return datesToEventWindows(dates, insight.subject_label ?? tag.name);
  }

  const symptom = symptomHeatmap.symptoms.find((row) => row.symptom_id === insight.subject_id);
  if (!symptom) return [];
  const dates = symptom.days.filter((day) => day.count > 0).map((day) => day.date);
  return datesToEventWindows(dates, insight.subject_label ?? symptom.name);
}

/** #488: resolve a lag insight's feature (antecedent) to a matchable slug/name. */
export function lagFeature(
  insight: InsightResponse
): { kind: 'tag' | 'symptom'; slug: string | null; name: string | null } | null {
  const kind = lagFeatureKind(insight);
  if (!kind) return null;
  const feature = (insight.payload as Record<string, unknown>).feature as Record<string, unknown>;
  const rawSlug = typeof feature.slug === 'string' ? feature.slug : null;
  const rawKey = typeof feature.key === 'string' ? feature.key : null;
  const slug = rawSlug ?? (rawKey ? rawKey.replace(/^(tag|symptom):/, '') : null);
  const name = typeof feature.name === 'string' ? feature.name : null;
  return { kind, slug, name };
}

/**
 * Dev fixtures: derive a lag insight's onset windows from its *feature*
 * (the antecedent), since the subject is the outcome and may be a metric.
 */
export function devLagEventWindowsFromHeatmaps(
  insight: InsightResponse,
  tagHeatmap: TagHeatmapResponse,
  symptomHeatmap: SymptomHeatmapResponse
): EventWindow[] {
  const feature = lagFeature(insight);
  if (!feature) return [];
  const matches = (rowSlug: string, rowName: string): boolean =>
    (feature.slug !== null && rowSlug.toLowerCase() === feature.slug.toLowerCase()) ||
    (feature.name !== null && rowName.toLowerCase() === feature.name.toLowerCase());

  if (feature.kind === 'tag') {
    const tag = tagHeatmap.tags.find((row) => matches(row.slug, row.name));
    if (!tag) return [];
    const dates = tag.days.filter((day) => day.count > 0).map((day) => day.date);
    return datesToEventWindows(dates, feature.name ?? tag.name);
  }

  const symptom = symptomHeatmap.symptoms.find((row) => matches(row.slug, row.name));
  if (!symptom) return [];
  const dates = symptom.days.filter((day) => day.count > 0).map((day) => day.date);
  return datesToEventWindows(dates, feature.name ?? symptom.name);
}
