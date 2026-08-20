import type { InsightDigestResponse } from '$lib/api/insights';
import type { UserPreferencesResponse } from '$lib/api/preferences';

/**
 * Decide whether to show the one-time weekly digest modal (#739).
 *
 * Fires only for a *persisted* weekly digest (stable `generated_at`) that is
 * newer than the last one the user acknowledged — so it appears once per
 * generated digest, never for the on-demand recompute fallback
 * (`generated_at == null`) and never twice for the same week. Yields to an open
 * onboarding/entry sheet, mirroring `shouldShowMaturityExpectationIntro`.
 */
export function shouldShowWeeklyDigestModal(options: {
  preferences: UserPreferencesResponse | null | undefined;
  digest: InsightDigestResponse | null | undefined;
  blockingSheetOpen?: boolean;
}): boolean {
  const { preferences, digest, blockingSheetOpen = false } = options;
  if (!preferences || !digest || blockingSheetOpen) return false;
  if (!preferences.digest_enabled) return false;
  if (digest.insights.length === 0) return false;

  const generatedAt = digest.generated_at;
  if (!generatedAt) return false;

  const generatedMs = Date.parse(generatedAt);
  if (Number.isNaN(generatedMs)) return false;

  const lastSeen = preferences.last_seen_digest_at;
  if (!lastSeen) return true;

  const lastSeenMs = Date.parse(lastSeen);
  if (Number.isNaN(lastSeenMs)) return true;

  return generatedMs > lastSeenMs;
}
