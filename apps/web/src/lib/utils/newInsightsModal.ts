/**
 * Gate for the once-daily “new insights since last ack” modal.
 */

import type { InsightResponse } from '$lib/api/insights';
import type { UserPreferencesResponse } from '$lib/api/preferences';
import { localIsoDate } from '$lib/utils/home';
import { rankInsights } from '$lib/utils/insightRanking';

export const NEW_INSIGHTS_MODAL_TOP_N = 3;
export const NEW_INSIGHTS_POPUP_DAY_KEY = 'correlcore:new-insights-popup-day';

export function readNewInsightsPopupDay(
  storage: Pick<Storage, 'getItem'> | null | undefined = typeof localStorage !== 'undefined'
    ? localStorage
    : null
): string | null {
  if (!storage) return null;
  try {
    return storage.getItem(NEW_INSIGHTS_POPUP_DAY_KEY);
  } catch {
    return null;
  }
}

export function markNewInsightsPopupDay(
  dayIso: string,
  storage: Pick<Storage, 'setItem'> | null | undefined = typeof localStorage !== 'undefined'
    ? localStorage
    : null
): void {
  if (!storage) return;
  try {
    storage.setItem(NEW_INSIGHTS_POPUP_DAY_KEY, dayIso);
  } catch {
    /* ignore quota / private mode */
  }
}

/** Insights newer than the prefs high-water mark, ranked, capped. */
export function selectNewInsightsSinceLastSeen(
  insights: readonly InsightResponse[],
  lastSeenInsightAt: string | null | undefined,
  options: { dismissedIds?: readonly string[]; limit?: number } = {}
): InsightResponse[] {
  const dismissed = new Set(options.dismissedIds ?? []);
  const lastSeenMs = lastSeenInsightAt ? Date.parse(lastSeenInsightAt) : Number.NaN;
  const hasLastSeen = !Number.isNaN(lastSeenMs);

  const fresh = insights.filter((insight) => {
    if (dismissed.has(insight.id)) return false;
    const generatedMs = Date.parse(insight.generated_at);
    if (Number.isNaN(generatedMs)) return false;
    if (!hasLastSeen) return true;
    return generatedMs > lastSeenMs;
  });

  return rankInsights(fresh).slice(0, options.limit ?? NEW_INSIGHTS_MODAL_TOP_N);
}

export function maxInsightGeneratedAt(insights: readonly InsightResponse[]): string | null {
  let maxMs = Number.NEGATIVE_INFINITY;
  let maxIso: string | null = null;
  for (const insight of insights) {
    const ms = Date.parse(insight.generated_at);
    if (Number.isNaN(ms)) continue;
    if (ms > maxMs) {
      maxMs = ms;
      maxIso = insight.generated_at;
    }
  }
  return maxIso;
}

/**
 * Decide whether to show the new-insights popup.
 *
 * Yields to entry sheet and weekly digest modal. Caps to one show per local
 * calendar day via ``alreadyShownToday``. Content gate: at least one insight
 * newer than ``last_seen_insight_at``.
 */
export function shouldShowNewInsightsModal(options: {
  preferences: UserPreferencesResponse | null | undefined;
  insights: readonly InsightResponse[] | null | undefined;
  dismissedIds?: readonly string[];
  blockingSheetOpen?: boolean;
  digestModalOpen?: boolean;
  alreadyShownToday?: boolean;
  now?: Date;
}): { show: boolean; candidates: InsightResponse[] } {
  const {
    preferences,
    insights,
    dismissedIds = [],
    blockingSheetOpen = false,
    digestModalOpen = false,
    alreadyShownToday = false,
  } = options;

  if (!preferences || !insights || blockingSheetOpen || digestModalOpen || alreadyShownToday) {
    return { show: false, candidates: [] };
  }
  if (preferences.analytics_enabled === false) {
    return { show: false, candidates: [] };
  }

  const candidates = selectNewInsightsSinceLastSeen(insights, preferences.last_seen_insight_at, {
    dismissedIds,
    limit: NEW_INSIGHTS_MODAL_TOP_N,
  });

  return { show: candidates.length > 0, candidates };
}

export function isNewInsightsPopupAlreadyShownToday(
  now: Date = new Date(),
  storage?: Pick<Storage, 'getItem'> | null
): boolean {
  const stored = readNewInsightsPopupDay(storage);
  if (!stored) return false;
  return stored === localIsoDate(now);
}
