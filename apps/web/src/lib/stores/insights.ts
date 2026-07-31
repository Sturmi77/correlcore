/**
 * InsightStore — Issue #167 (M3.1) + #601 Phase 1 subject-stable dismiss.
 *
 * Best-effort store for analytics insights. A load failure MUST NOT propagate
 * an error state to unrelated Home screen components (especially the
 * `+ Log today` CTA button). The store is deliberately isolated: callers
 * check `loading` / `error` independently of other page state.
 *
 * State contract (FRONTEND.md §8):
 *   - `loading`      — true while the API call is in-flight
 *   - `insights`     — newest-per-subject insights from GET /api/v1/insights/latest
 *   - `latest`       — highest confidence × effect_size non-dismissed insight
 *   - `error`        — human-readable error string; null on success; never re-thrown
 *   - `insightMaturity` — backend-owned maturity phase for insight UI
 *   - `dismissedIds` — insight IDs hidden optimistically / from dismissals list
 *   - `dismissalIdByInsightId` — maps insight id → dismissal row id for Undo
 */

import { writable, derived, get } from 'svelte/store';
import {
  createInsightDismissal,
  deleteInsightDismissal,
  deleteInsightDismissalByInsightId,
  listInsightDismissals,
  listLatestInsights,
  type InsightDismissalResponse,
  type InsightMaturity,
  type InsightResponse,
} from '$lib/api/insights';
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
  dismissalIdByInsightId: Record<string, string>;
}

const _state = writable<InsightStoreState>({
  insights: [],
  insightMaturity: null,
  latest: null,
  loading: false,
  error: null,
  dismissedIds: [],
  dismissalIdByInsightId: {},
});

export const insightStore = { subscribe: _state.subscribe };

/** Derived: all non-dismissed insights sorted by confidence × effect_size desc. */
export const rankedInsights = derived(_state, ($s) =>
  rankInsights($s.insights.filter((i) => !$s.dismissedIds.includes(i.id)))
);

function pickLatest(insights: InsightResponse[], dismissedIds: string[]): InsightResponse | null {
  const visible = insights.filter((i) => !dismissedIds.includes(i.id));
  if (visible.length === 0) return null;
  return rankInsights(visible)[0] ?? null;
}

async function loadDismissalState(): Promise<{
  dismissedIds: string[];
  dismissalIdByInsightId: Record<string, string>;
}> {
  try {
    const response = await listInsightDismissals();
    const dismissedIds: string[] = [];
    const dismissalIdByInsightId: Record<string, string> = {};
    for (const dismissal of response.dismissals) {
      const insightId = dismissal.insight?.id ?? dismissal.insight_id;
      if (!insightId) continue;
      dismissedIds.push(insightId);
      dismissalIdByInsightId[insightId] = dismissal.id;
    }
    return { dismissedIds, dismissalIdByInsightId };
  } catch {
    return { dismissedIds: [], dismissalIdByInsightId: {} };
  }
}

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

  const dismissalState = await loadDismissalState();

  try {
    if (get(devForceVisualizations)) {
      const fixture = getDevPhaseFixture(get(devPhase));
      const latest = pickLatest(fixture.insights, dismissalState.dismissedIds);
      _state.set({
        insights: fixture.insights,
        insightMaturity: fixture.maturity,
        latest,
        loading: false,
        error: null,
        ...dismissalState,
      });
      return;
    }

    const response = await listLatestInsights({ limit: 50 });
    const insights = response.insights;
    const latest = pickLatest(insights, dismissalState.dismissedIds);
    _state.set({
      insights,
      insightMaturity: response.insight_maturity,
      latest,
      loading: false,
      error: null,
      ...dismissalState,
    });
  } catch (err) {
    const error = err instanceof Error ? err.message : 'Failed to load insights';
    _state.update((s) => ({ ...s, loading: false, error }));
  }
}

/**
 * Dismiss an insight by ID (subject-stable on the server).
 *
 * - Immediately removes the insight from `latest` and the ranked list.
 * - POST /insights/dismissals best-effort.
 */
export async function dismissInsight(id: string): Promise<InsightDismissalResponse | null> {
  const current = get(_state);
  if (current.dismissedIds.includes(id)) return null;

  const dismissedIds = [...current.dismissedIds, id];
  const latest = pickLatest(current.insights, dismissedIds);
  _state.update((s) => ({ ...s, dismissedIds, latest }));

  try {
    const dismissal = await createInsightDismissal(id);
    _state.update((s) => ({
      ...s,
      dismissalIdByInsightId: { ...s.dismissalIdByInsightId, [id]: dismissal.id },
    }));
    return dismissal;
  } catch {
    return null;
  }
}

/**
 * Undo a dismiss — restore the insight to the active feed ranking.
 *
 * Prefers DELETE /dismissals/{id}; falls back to by-insight when unknown.
 */
export async function undismissInsight(id: string): Promise<void> {
  const current = get(_state);
  if (!current.dismissedIds.includes(id)) return;

  const dismissalId = current.dismissalIdByInsightId[id];
  const dismissedIds = current.dismissedIds.filter((dismissedId) => dismissedId !== id);
  const { [id]: _removed, ...dismissalIdByInsightId } = current.dismissalIdByInsightId;
  const latest = pickLatest(current.insights, dismissedIds);
  _state.update((s) => ({ ...s, dismissedIds, dismissalIdByInsightId, latest }));

  try {
    if (dismissalId) {
      await deleteInsightDismissal(dismissalId);
    } else {
      await deleteInsightDismissalByInsightId(id);
    }
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
    dismissalIdByInsightId: {},
  });
}
