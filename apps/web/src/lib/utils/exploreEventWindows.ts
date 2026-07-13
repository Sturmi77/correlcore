import type { EntryResponse } from '$lib/api/entries';
import type { InsightResponse } from '$lib/api/insights';
import type { SymptomHeatmapResponse, TagHeatmapResponse } from '$lib/api/stats';
import type { EventWindow } from '$lib/components/trends/EventAlignedSmallMultiplesSheet.svelte';
import type { MetricKey } from '$lib/utils/charts';

/** ADR-0035 §6: only tag/symptom subjects have per-day presence windows. */
export function isExploreEventsSubject(insight: InsightResponse): boolean {
  return insight.subject_type === 'tag' || insight.subject_type === 'symptom';
}

export function insightMetricToChartKey(metric: string | null | undefined): MetricKey {
  if (metric === 'energy' || metric === 'energy_avg') return 'energy_avg';
  if (metric === 'stress' || metric === 'stress_avg') return 'stress_avg';
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
