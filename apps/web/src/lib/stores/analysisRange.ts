import { browser } from '$app/environment';
import { writable } from 'svelte/store';
import type { TagCooccurrenceRange } from '$lib/api/insights';
import type { TimeseriesRange } from '$lib/api/stats';
import { cooccurrenceRangeToTimeseries, isTimeseriesRange } from '$lib/utils/analysisRange';

const STORAGE_KEY = 'cc_analysis_range';
const LEGACY_COOCCURRENCE_KEY = 'cc_insights_cooccurrence_range';

function readLegacyCooccurrenceRange(): TimeseriesRange | null {
  if (!browser) return null;
  try {
    const legacy = localStorage.getItem(LEGACY_COOCCURRENCE_KEY);
    if (legacy === '30d' || legacy === '90d' || legacy === '1y') {
      return cooccurrenceRangeToTimeseries(legacy as TagCooccurrenceRange);
    }
  } catch {
    // ignore
  }
  return null;
}

function readInitial(): TimeseriesRange {
  if (!browser) return 'week';
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored && isTimeseriesRange(stored)) {
      return stored;
    }
  } catch {
    // sandboxed / private mode
  }
  return readLegacyCooccurrenceRange() ?? 'week';
}

function createAnalysisRangeStore() {
  const { subscribe, set } = writable<TimeseriesRange>(readInitial());

  return {
    subscribe,
    set(range: TimeseriesRange) {
      if (!isTimeseriesRange(range)) return;
      if (browser) {
        try {
          localStorage.setItem(STORAGE_KEY, range);
          localStorage.removeItem(LEGACY_COOCCURRENCE_KEY);
        } catch {
          // ignore
        }
      }
      set(range);
    },
  };
}

export const analysisRange = createAnalysisRangeStore();

export function setAnalysisRange(range: TimeseriesRange): void {
  analysisRange.set(range);
}
