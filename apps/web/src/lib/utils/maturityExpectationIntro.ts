import type { UserPreferencesResponse } from '$lib/api/preferences';

/** Phases shown on the one-time onboarding maturity expectation card. */
export const MATURITY_INTRO_PHASES = [
  'collecting',
  'early_patterns',
  'provisional',
  'robust',
] as const;

export type MaturityIntroPhase = (typeof MATURITY_INTRO_PHASES)[number];

export const MATURITY_INTRO_THUMBS: Record<MaturityIntroPhase, string> = {
  collecting: '/onboarding/maturity/phase1_collecting.png',
  early_patterns: '/onboarding/maturity/phase2_early_patterns.png',
  provisional: '/onboarding/maturity/phase3_provisional.png',
  robust: '/onboarding/maturity/phase4_robust.png',
};

/**
 * Show the expectation sheet once the user has at least one entry and has not
 * dismissed the intro. Never while the entry sheet is open.
 */
export function shouldShowMaturityExpectationIntro(options: {
  preferences: UserPreferencesResponse | null | undefined;
  entryCount: number | null | undefined;
  entrySheetOpen: boolean;
}): boolean {
  const { preferences, entryCount, entrySheetOpen } = options;
  if (!preferences || entrySheetOpen) return false;
  if (preferences.onboarding_maturity_intro_seen) return false;
  return (entryCount ?? 0) >= 1;
}
