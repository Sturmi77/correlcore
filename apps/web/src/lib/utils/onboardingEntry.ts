import type { UserPreferencesResponse } from '$lib/api/preferences';

/** Summary step is skipped when the user picked at most this many tags (O-37). */
export const ONBOARDING_SUMMARY_SKIP_MAX_TAGS = 3;

export function shouldShowOnboardingTags(
  preferences: UserPreferencesResponse | null | undefined,
  entryCount: number | null | undefined
): boolean {
  return Boolean(
    preferences && !preferences.onboarding_retro_completed && (entryCount ?? 0) === 0
  );
}

export function shouldSkipOnboardingSummary(tagCount: number): boolean {
  return tagCount <= ONBOARDING_SUMMARY_SKIP_MAX_TAGS;
}
