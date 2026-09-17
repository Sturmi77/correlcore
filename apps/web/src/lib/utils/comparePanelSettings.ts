import { browser } from '$app/environment';
import { isCompareZoomStage, type CompareZoomStageIndex } from '$lib/utils/compareAxisZoom';

export type CompareMode = 'lines' | 'strips';
export type CompareSortMode = 'frequency' | 'recent' | 'correlation' | 'pinned' | 'clustered';
export type { CompareZoomStageIndex };

export const COMPARE_MODE_KEY = 'cc_trend_compare_mode';
export const COMPARE_SORT_KEY = 'cc_trend_compare_sort';
export const COMPARE_ZOOM_KEY = 'cc_trend_compare_zoom';
export const COMPARE_COINCIDENCE_KEY = 'cc_trend_compare_coincidence';
export const COMPARE_LAG1_KEY = 'cc_trend_compare_lag1';
export const COMPARE_OVERLAY_HINT_KEY = 'cc_trend_compare_overlay_hint';
/** Default: stage 2 → 7 days/cell (CAZ-0). */
export const COMPARE_ZOOM_DEFAULT_STAGE: CompareZoomStageIndex = 2;

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
    // storage-exempt: generic helper, callers pass compare-panel UI keys only
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
      value === 'frequency' ||
      value === 'recent' ||
      value === 'correlation' ||
      value === 'pinned' ||
      value === 'clustered'
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
    value === 'frequency' ||
    value === 'recent' ||
    value === 'correlation' ||
    value === 'pinned' ||
    value === 'clustered'
  );
}

export function readCompareZoomStage(): CompareZoomStageIndex {
  return readLocal<CompareZoomStageIndex>(
    COMPARE_ZOOM_KEY,
    COMPARE_ZOOM_DEFAULT_STAGE,
    isCompareZoomStage
  );
}

export function writeCompareZoomStage(stage: CompareZoomStageIndex): void {
  writeLocal(COMPARE_ZOOM_KEY, stage);
}

/** #908: user preference for highlighting A∩B soft bands on Compare. */
export function readCompareCoincidenceHighlight(): boolean {
  return readLocal<boolean>(COMPARE_COINCIDENCE_KEY, false, (value) => typeof value === 'boolean');
}

export function writeCompareCoincidenceHighlight(enabled: boolean): void {
  writeLocal(COMPARE_COINCIDENCE_KEY, enabled);
}

/** #910: user preference for highlighting A→B (+1d) sequences on Compare. */
export function readCompareLag1Highlight(): boolean {
  return readLocal<boolean>(COMPARE_LAG1_KEY, false, (value) => typeof value === 'boolean');
}

export function writeCompareLag1Highlight(enabled: boolean): void {
  writeLocal(COMPARE_LAG1_KEY, enabled);
}

/** #919: the pin nudge fires once; dismissal is permanent. */
export function readCompareOverlayHintDismissed(): boolean {
  return readLocal<boolean>(COMPARE_OVERLAY_HINT_KEY, false, (value) => typeof value === 'boolean');
}

export function writeCompareOverlayHintDismissed(dismissed: boolean): void {
  writeLocal(COMPARE_OVERLAY_HINT_KEY, dismissed);
}

export { isCompareZoomStage };
