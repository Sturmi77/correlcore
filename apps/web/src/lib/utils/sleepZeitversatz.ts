/**
 * Phase 14 — labeled Compare Zeitversatz: shift sleep series +1 calendar day
 * so prior-night sleep sits next to next-day mood/energy. Not Lag-1 Abfolge.
 */

import type { TimeseriesPoint } from '$lib/api/stats';
import type { MetricKey } from '$lib/utils/charts';
import { shiftIsoDate } from '$lib/utils/streak';

export const SLEEP_ZEITVERSATZ_KEYS: readonly MetricKey[] = [
  'sleep_minutes_avg',
  'sleep_quality_avg',
] as const;

const STORAGE_KEY = 'trends.compare.sleepZeitversatz';

export function isSleepZeitversatzMetric(key: MetricKey): boolean {
  return (SLEEP_ZEITVERSATZ_KEYS as readonly string[]).includes(key);
}

/** Move sleep values from day D onto day D+1 (drop last day's sleep; first day null). */
export function applySleepZeitversatz(
  points: readonly TimeseriesPoint[],
  enabled: boolean
): TimeseriesPoint[] {
  if (!enabled || points.length === 0) return [...points];

  const byDate = new Map(points.map((point) => [point.period_start, point]));
  return points.map((point) => {
    const priorDate = shiftIsoDate(point.period_start, -1);
    const prior = byDate.get(priorDate);
    return {
      ...point,
      sleep_minutes_avg: prior?.sleep_minutes_avg ?? null,
      sleep_quality_avg: prior?.sleep_quality_avg ?? null,
    };
  });
}

export function readSleepZeitversatzPreference(storage: Storage | null): boolean {
  if (!storage) return false;
  try {
    return storage.getItem(STORAGE_KEY) === 'true';
  } catch {
    return false;
  }
}

export function writeSleepZeitversatzPreference(storage: Storage | null, value: boolean): void {
  if (!storage) return;
  try {
    storage.setItem(STORAGE_KEY, value ? 'true' : 'false');
  } catch {
    /* ignore quota / private mode */
  }
}
