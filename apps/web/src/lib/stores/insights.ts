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
 *   - `insightMaturity` — backend-owned maturity phase for insight UI
 *   - `dismissedIds` — insight IDs the user has dismissed (persisted to prefs)
 */

import { writable, derived, get } from 'svelte/store';
import { listInsights, type InsightMaturity, type InsightResponse } from '$lib/api/insights';
import { fetchUserPreferences, updateUserPreferences } from '$lib/api/preferences';
import { devForceVisualizations, devPhase } from '$lib/stores/devMode';
import { getDevPhaseFixture } from '$lib/dev/phaseFixtures';
import { rankInsights } from '$lib/utils/insightRanking';

export interface InsightStoreState {
  insights: InsightResponse[];
  insightMaturity: InsightMaturity | null;
  latest: InsightResponse | null;
  loading: boolean;
  error: string | null;
  dismissedIds: string[];
}

// ─── Internal writable ────────────────────────────────────────────────────────

const _state = writable<InsightStoreState>({
  insights: [],
  insightMaturity: null,
  latest: null,
  loading: false,
  error: null,
  dismissedIds: [],
});

// ─── Public read-only surface ─────────────────────────────────────────────────

export const insightStore = { subscribe: _state.subscribe };

/** Derived: all non-dismissed insights sorted by confidence × effect_size desc. */
export const rankedInsights = derived(_state, ($s) =>
  rankInsights($s.insights.filter((i) => !$s.dismissedIds.includes(i.id)))
);

// ─── Helpers ──────────────────────────────────────────────────────────────────

/** Resolve the highest-ranked non-dismissed insight from a list. */
function pickLatest(insights: InsightResponse[], dismissedIds: string[]): InsightResponse | null {
  const visible = insights.filter((i) => !dismissedIds.includes(i.id));
  if (visible.length === 0) return null;
  return rankInsights(visible)[0] ?? null;
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
      const fixture = getDevPhaseFixture(get(devPhase));
      const latest = pickLatest(fixture.insights, dismissedIds);
      _state.set({
        insights: fixture.insights,
        insightMaturity: fixture.maturity,
        latest,
        loading: false,
        error: null,
        dismissedIds,
      });
      return;
    }

    const response = await listInsights();
    const insights = response.insights;
    const latest = pickLatest(insights, dismissedIds);
    _state.set({
      insights,
      insightMaturity: response.insight_maturity,
      latest,
      loading: false,
      error: null,
      dismissedIds,
    });
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
    insightMaturity: null,
    latest: null,
    loading: false,
    error: null,
    dismissedIds: [],
  });
}
