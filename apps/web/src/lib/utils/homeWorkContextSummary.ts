import type { WorkContextSummaryItem } from '$lib/api/dashboard';

const MOOD_SCALE_MAX = 5;

export type WorkContextDisplayItem = WorkContextSummaryItem & {
  moodDelta: number | null;
};

export function weightedMoodAverage(items: WorkContextSummaryItem[]): number | null {
  const withMood = items.filter((item) => item.mood_avg !== null && item.entry_count > 0);
  if (!withMood.length) return null;

  const totalWeight = withMood.reduce((sum, item) => sum + item.entry_count, 0);
  if (totalWeight <= 0) return null;

  const weighted = withMood.reduce((sum, item) => sum + item.mood_avg! * item.entry_count, 0);
  return weighted / totalWeight;
}

export function buildWorkContextDisplayItems(
  items: WorkContextSummaryItem[],
  limit = 4
): WorkContextDisplayItem[] {
  const overallMood = weightedMoodAverage(items);
  return items
    .filter((item) => item.entry_count > 0 && item.mood_avg !== null)
    .map((item) => ({
      ...item,
      moodDelta: overallMood === null ? null : item.mood_avg! - overallMood,
    }))
    .sort((a, b) => {
      const deltaA = Math.abs(a.moodDelta ?? 0);
      const deltaB = Math.abs(b.moodDelta ?? 0);
      if (deltaB !== deltaA) return deltaB - deltaA;
      if (b.entry_count !== a.entry_count) return b.entry_count - a.entry_count;
      return a.work_context.localeCompare(b.work_context);
    })
    .slice(0, limit);
}

export function workContextMoodBarWidth(moodAvg: number | null): string {
  if (moodAvg === null) return '0%';
  const ratio = Math.min(MOOD_SCALE_MAX, Math.max(0, moodAvg)) / MOOD_SCALE_MAX;
  return `${ratio * 100}%`;
}
