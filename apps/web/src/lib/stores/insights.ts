/**
 * InsightStore — Issue #167 (M3.1).
 *
 * Best-effort store for analytics insights. A load failure MUST NOT propagate
 * an error state to unrelated Home screen components (especially the
 * `+ Log today` CTA button). The store is deliberately isolated: callers
 * check `loading` / `error` independently of other page state.
 *
 * State contract (FRONTEND.md §8):
 *   - `loading`      — true while the API call is in-flight
 *   - `insights`     — all insights from GET /api/v1/insights
 *   - `latest`       — highest confidence × effect_size non-dismissed insight
 *   - `error`        — human-readable error string; null on success; never re-thrown
 *   - `dismissedIds` — insight IDs the user has dismissed (persisted to prefs)
 */

import { writable, derived, get } from 'svelte/store';
import { listInsights, type InsightResponse } from '$lib/api/insights';
import { fetchUserPreferences, updateUserPreferences } from '$lib/api/preferences';
import { devForceVisualizations } from '$lib/stores/devMode';
import { mockInsights } from '$lib/dev/mockInsights';

export interface InsightStoreState {
  insights: InsightResponse[];
  latest: InsightResponse | null;
  loading: boolean;
  error: string | null;
  dismissedIds: string[];
}

// ─── Internal writable ────────────────────────────────────────────────────────

const _state = writable<InsightStoreState>({
  insights: [],
  latest: null,
  loading: false,
  error: null,
  dismissedIds: [],
});

// ─── Public read-only surface ─────────────────────────────────────────────────

export const insightStore = { subscribe: _state.subscribe };

/** Derived: all non-dismissed insights sorted by confidence × effect_size desc. */
export const rankedInsights = derived(_state, ($s) =>
  $s.insights
    .filter((i) => !$s.dismissedIds.includes(i.id))
    .sort(
      (a, b) =>
        (b.confidence ?? 0) * Math.abs(b.effect_size ?? 0) -
        (a.confidence ?? 0) * Math.abs(a.effect_size ?? 0)
    )
);

// ─── Helpers ──────────────────────────────────────────────────────────────────

/** Resolve the highest-ranked non-dismissed insight from a list. */
function pickLatest(insights: InsightResponse[], dismissedIds: string[]): InsightResponse | null {
  const visible = insights.filter((i) => !dismissedIds.includes(i.id));
  if (visible.length === 0) return null;
  return visible.reduce((best, curr) =>
    (curr.confidence ?? 0) * Math.abs(curr.effect_size ?? 0) >
    (best.confidence ?? 0) * Math.abs(best.effect_size ?? 0)
      ? curr
      : best
  );
}

/**
 * Load dismissed IDs from user preferences.
 * Falls back to an empty array on any error (SSR-safe — no localStorage).
 */
async function loadDismissedIds(): Promise<string[]> {
  try {
    const prefs = await fetchUserPreferences();
    return prefs.dismissed_insight_keys ?? [];
  } catch {
    return [];
  }
}

// ─── Actions ──────────────────────────────────────────────────────────────────

/**
 * Load insights from the API.
 *
 * - Sets `loading: true` while in-flight.
 * - On success: populates `insights`, `latest`, clears `error`.
 * - On failure: sets `error` string, keeps `insights` as-is — NEVER throws.
 *
 * Home CTA must remain interactive regardless of this call's outcome.
 */
export async function loadInsights(): Promise<void> {
  _state.update((s) => ({ ...s, loading: true, error: null }));

  // Load dismissed IDs in parallel — failure is non-fatal
  const dismissedIds = await loadDismissedIds();

  try {
    if (get(devForceVisualizations)) {
      const latest = pickLatest(mockInsights, dismissedIds);
      _state.set({ insights: mockInsights, latest, loading: false, error: null, dismissedIds });
      return;
    }

    const response = await listInsights();
    const insights = response.insights;
    const latest = pickLatest(insights, dismissedIds);
    _state.set({ insights, latest, loading: false, error: null, dismissedIds });
  } catch (err) {
    const error = err instanceof Error ? err.message : 'Failed to load insights';
    // Update only the error + loading fields — keep any previously loaded insights
    _state.update((s) => ({ ...s, loading: false, error }));
  }
}

/**
 * Dismiss an insight by ID.
 *
 * - Immediately removes the insight from `latest` and the ranked list.
 * - Fires PATCH /user/preferences in the background (best-effort).
 * - A preferences-save failure is silently swallowed — the UI stays consistent.
 */
export async function dismissInsight(id: string): Promise<void> {
  const current = get(_state);
  if (current.dismissedIds.includes(id)) return; // idempotent

  const dismissedIds = [...current.dismissedIds, id];
  const latest = pickLatest(current.insights, dismissedIds);
  _state.update((s) => ({ ...s, dismissedIds, latest }));

  // Best-effort persist — never block the UI on this
  try {
    await updateUserPreferences({ dismissed_insight_keys: dismissedIds });
  } catch {
    // intentionally swallowed — UI is already updated optimistically
  }
}

/** Reset the store — call on logout. */
export function resetInsightStore(): void {
  _state.set({
    insights: [],
    latest: null,
    loading: false,
    error: null,
    dismissedIds: [],
  });
}
