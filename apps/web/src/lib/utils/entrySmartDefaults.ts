import type { EntryMetrics } from '$lib/api/entries';

export const NEUTRAL_SCALE_DEFAULT = 3;

export function scaleDefaultsFromPrevious(
  previous: EntryMetrics | null | undefined
): Pick<EntryMetrics, 'mood_score' | 'energy' | 'stress'> | null {
  if (!previous) return null;
  return {
    mood_score: previous.mood_score,
    energy: previous.energy,
    stress: previous.stress,
  };
}
