import { browser } from '$app/environment';

export type CompareMode = 'lines' | 'strips';
export type CompareSortMode = 'frequency' | 'recent' | 'correlation' | 'pinned';

export const COMPARE_MODE_KEY = 'cc_trend_compare_mode';
export const COMPARE_SORT_KEY = 'cc_trend_compare_sort';

function readLocal<T>(key: string, fallback: T, isValid: (value: unknown) => boolean): T {
  if (!browser) return fallback;
  try {
    const raw = window.localStorage.getItem(key);
    if (raw === null) return fallback;
    const parsed = JSON.parse(raw);
    return isValid(parsed) ? (parsed as T) : fallback;
  } catch {
    return fallback;
  }
}

function writeLocal(key: string, value: unknown): void {
  if (!browser) return;
  try {
    window.localStorage.setItem(key, JSON.stringify(value));
  } catch {
    // Quota or private-mode — silently ignore.
  }
}

export function readCompareMode(): CompareMode {
  return readLocal<CompareMode>(
    COMPARE_MODE_KEY,
    'lines',
    (value) => value === 'lines' || value === 'strips'
  );
}

export function writeCompareMode(mode: CompareMode): void {
  writeLocal(COMPARE_MODE_KEY, mode);
}

export function readCompareSortMode(): CompareSortMode {
  return readLocal<CompareSortMode>(
    COMPARE_SORT_KEY,
    'frequency',
    (value) =>
      value === 'frequency' || value === 'recent' || value === 'correlation' || value === 'pinned'
  );
}

export function writeCompareSortMode(sortMode: CompareSortMode): void {
  writeLocal(COMPARE_SORT_KEY, sortMode);
}

export function isCompareMode(value: unknown): value is CompareMode {
  return value === 'lines' || value === 'strips';
}

export function isCompareSortMode(value: unknown): value is CompareSortMode {
  return (
    value === 'frequency' || value === 'recent' || value === 'correlation' || value === 'pinned'
  );
}
