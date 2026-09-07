/**
 * Gate for the once-daily “new insights since last ack” modal.
 */

import type { InsightResponse } from '$lib/api/insights';
import type { UserPreferencesResponse } from '$lib/api/preferences';
import { localIsoDate } from '$lib/utils/home';
import { rankInsights } from '$lib/utils/insightRanking';

export const NEW_INSIGHTS_MODAL_TOP_N = 3;
/** Prefix only — full key is `${prefix}${userId}` so accounts do not share the day gate. */
export const NEW_INSIGHTS_POPUP_DAY_KEY_PREFIX = 'correlcore:new-insights-popup-day:';

export function newInsightsPopupDayKey(userId: string): string {
  return `${NEW_INSIGHTS_POPUP_DAY_KEY_PREFIX}${userId}`;
}

export function readNewInsightsPopupDay(
  userId: string,
  storage: Pick<Storage, 'getItem'> | null | undefined = typeof localStorage !== 'undefined'
    ? localStorage
    : null
): string | null {
  if (!userId || !storage) return null;
  try {
    return storage.getItem(newInsightsPopupDayKey(userId));
  } catch {
    return null;
  }
}

export function markNewInsightsPopupDay(
  userId: string,
  dayIso: string,
  storage: Pick<Storage, 'setItem'> | null | undefined = typeof localStorage !== 'undefined'
    ? localStorage
    : null
): void {
  if (!userId || !storage) return;
  try {
    // storage-exempt: per-user UX day gate (prefix + userId); ISO date only, no auth material
    storage.setItem(newInsightsPopupDayKey(userId), dayIso);
  } catch {
    /* ignore quota / private mode */
  }
}

/** Fresh insights newer than the prefs high-water mark (uncapped, unranked). */
export function filterFreshInsightsSinceLastSeen(
  insights: readonly InsightResponse[],
  lastSeenInsightAt: string | null | undefined,
  options: { dismissedIds?: readonly string[] } = {}
): InsightResponse[] {
  const dismissed = new Set(options.dismissedIds ?? []);
  const lastSeenMs = lastSeenInsightAt ? Date.parse(lastSeenInsightAt) : Number.NaN;
  const hasLastSeen = !Number.isNaN(lastSeenMs);

  return insights.filter((insight) => {
    if (dismissed.has(insight.id)) return false;
    const generatedMs = Date.parse(insight.generated_at);
    if (Number.isNaN(generatedMs)) return false;
    if (!hasLastSeen) return true;
    return generatedMs > lastSeenMs;
  });
}

/** Insights newer than the prefs high-water mark, ranked, capped. */
export function selectNewInsightsSinceLastSeen(
  insights: readonly InsightResponse[],
  lastSeenInsightAt: string | null | undefined,
  options: { dismissedIds?: readonly string[]; limit?: number } = {}
): InsightResponse[] {
  const fresh = filterFreshInsightsSinceLastSeen(insights, lastSeenInsightAt, options);
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
 *
 * ``ackHighWater`` is the newest ``generated_at`` among *all* fresh insights
 * (not only the capped preview), so dismiss acknowledges the full batch.
 */
export function shouldShowNewInsightsModal(options: {
  preferences: UserPreferencesResponse | null | undefined;
  insights: readonly InsightResponse[] | null | undefined;
  dismissedIds?: readonly string[];
  blockingSheetOpen?: boolean;
  digestModalOpen?: boolean;
  alreadyShownToday?: boolean;
  now?: Date;
}): { show: boolean; candidates: InsightResponse[]; ackHighWater: string | null } {
  const {
    preferences,
    insights,
    dismissedIds = [],
    blockingSheetOpen = false,
    digestModalOpen = false,
    alreadyShownToday = false,
  } = options;

  if (!preferences || !insights || blockingSheetOpen || digestModalOpen || alreadyShownToday) {
    return { show: false, candidates: [], ackHighWater: null };
  }
  if (preferences.analytics_enabled === false) {
    return { show: false, candidates: [], ackHighWater: null };
  }

  const fresh = filterFreshInsightsSinceLastSeen(insights, preferences.last_seen_insight_at, {
    dismissedIds,
  });
  const candidates = rankInsights(fresh).slice(0, NEW_INSIGHTS_MODAL_TOP_N);
  const ackHighWater = maxInsightGeneratedAt(fresh);

  return { show: candidates.length > 0, candidates, ackHighWater };
}

export function isNewInsightsPopupAlreadyShownToday(
  userId: string,
  now: Date = new Date(),
  storage?: Pick<Storage, 'getItem'> | null
): boolean {
  const stored = readNewInsightsPopupDay(userId, storage);
  if (!stored) return false;
  return stored === localIsoDate(now);
}
