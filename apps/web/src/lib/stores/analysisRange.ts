import { browser } from '$app/environment';
import { writable } from 'svelte/store';
import type { TimeseriesRange } from '$lib/api/stats';
import { isTimeseriesRange } from '$lib/utils/analysisRange';
import {
  coerceTrendWindowDays,
  isTrendWindowDays,
  timeseriesRangeToTrendWindowDays,
  TREND_WINDOW_DAYS_DEFAULT,
  type TrendWindowDays,
} from '$lib/utils/trendWindowDays';

const ANALYSIS_RANGE_STORAGE_KEY = 'cc_analysis_range';
const TREND_WINDOW_STORAGE_KEY = 'cc_trend_window_days';
const LEGACY_COOCCURRENCE_KEY = 'cc_insights_cooccurrence_range';

function readInitial(): TrendWindowDays {
  if (!browser) return TREND_WINDOW_DAYS_DEFAULT;
  try {
    const storedDays = localStorage.getItem(TREND_WINDOW_STORAGE_KEY);
    if (storedDays && isTrendWindowDays(Number(storedDays))) {
      return Number(storedDays) as TrendWindowDays;
    }
    const storedRange = localStorage.getItem(ANALYSIS_RANGE_STORAGE_KEY);
    if (storedRange && isTimeseriesRange(storedRange)) {
      return timeseriesRangeToTrendWindowDays(storedRange);
    }
    const legacy = localStorage.getItem(LEGACY_COOCCURRENCE_KEY);
    if (legacy === '30d') return 28;
    if (legacy === '90d' || legacy === '1y') return 90;
  } catch {
    // sandboxed / private mode
  }
  return TREND_WINDOW_DAYS_DEFAULT;
}

function persist(days: TrendWindowDays): void {
  if (!browser) return;
  try {
    localStorage.setItem(TREND_WINDOW_STORAGE_KEY, String(days));
    // Keep legacy key in sync for older readers during rollout.
    localStorage.setItem(
      ANALYSIS_RANGE_STORAGE_KEY,
      days === 14 ? 'week' : days === 90 ? 'quarter' : 'month'
    );
    localStorage.removeItem(LEGACY_COOCCURRENCE_KEY);
  } catch {
    // ignore
  }
}

function createTrendWindowStore() {
  const { subscribe, set } = writable<TrendWindowDays>(readInitial());

  return {
    subscribe,
    set(days: TrendWindowDays) {
      const next = coerceTrendWindowDays(days);
      persist(next);
      set(next);
    },
    /** Hydrate from server preference without treating it as a user edit. */
    hydrateFromServer(days: unknown) {
      if (days == null) return;
      const next = coerceTrendWindowDays(days);
      persist(next);
      set(next);
    },
  };
}

/** Canonical analysis window in days (server preference + local cache). */
export const analysisRange = createTrendWindowStore();

export function setAnalysisRange(days: TrendWindowDays): void {
  analysisRange.set(days);
}

/** @deprecated Prefer TrendWindowDays; kept for call sites mid-migration. */
export function setAnalysisRangeFromTimeseries(range: TimeseriesRange): void {
  analysisRange.set(timeseriesRangeToTrendWindowDays(range));
}
