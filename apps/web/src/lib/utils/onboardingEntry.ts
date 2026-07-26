import type { UserPreferencesResponse } from '$lib/api/preferences';

/** Summary step is skipped when the user picked at most this many tags (O-37). */
export const ONBOARDING_SUMMARY_SKIP_MAX_TAGS = 3;

export type ShouldShowOnboardingTagsOptions = {
  /**
   * True when a deferred onboarding suggestion stash exists for this user
   * (close-before-recovery after an offline first save). Lets chips return
   * even though entry_count is already > 0.
   */
  hasDeferredSuggestionStash?: boolean;
};

export function shouldShowOnboardingTags(
  preferences: UserPreferencesResponse | null | undefined,
  entryCount: number | null | undefined,
  options?: ShouldShowOnboardingTagsOptions
): boolean {
  if (!preferences) return false;
  // Deferred stash must win over `onboarding_retro_completed`: finalize can
  // commit server-side before the entry tag save lands. Without this, a failed
  // post-finalize persist + remount hides chips forever while the first entry
  // never receives the suggestion tags.
  if (options?.hasDeferredSuggestionStash) return true;
  if (preferences.onboarding_retro_completed) return false;
  if ((entryCount ?? 0) === 0) return true;
  return false;
}

export function shouldSkipOnboardingSummary(tagCount: number): boolean {
  return tagCount <= ONBOARDING_SUMMARY_SKIP_MAX_TAGS;
}
