import { describe, expect, it } from 'vitest';
import {
  MATURITY_INTRO_PHASES,
  shouldShowMaturityExpectationIntro,
} from './maturityExpectationIntro';

const prefs = {
  user_id: 'u1',
  analytics_enabled: true,
  digest_enabled: true,
  onboarding_retro_completed: false,
  onboarding_profile_completed: false,
  onboarding_maturity_intro_seen: false,
  dismissed_insight_keys: [],
  reached_milestone_keys: [],
  last_seen_insight_at: null,
  created_at: '',
  updated_at: '',
};

describe('shouldShowMaturityExpectationIntro', () => {
  it('shows before first-entry tag onboarding', () => {
    expect(
      shouldShowMaturityExpectationIntro({
        preferences: prefs,
        entryCount: 0,
        entrySheetOpen: false,
      })
    ).toBe(true);
  });

  it('hides while the entry sheet is open', () => {
    expect(
      shouldShowMaturityExpectationIntro({
        preferences: prefs,
        entryCount: 0,
        entrySheetOpen: true,
      })
    ).toBe(false);
  });

  it('hides after dismiss, after onboarding, or once entries exist', () => {
    expect(
      shouldShowMaturityExpectationIntro({
        preferences: { ...prefs, onboarding_maturity_intro_seen: true },
        entryCount: 0,
        entrySheetOpen: false,
      })
    ).toBe(false);
    expect(
      shouldShowMaturityExpectationIntro({
        preferences: { ...prefs, onboarding_retro_completed: true },
        entryCount: 0,
        entrySheetOpen: false,
      })
    ).toBe(false);
    expect(
      shouldShowMaturityExpectationIntro({
        preferences: prefs,
        entryCount: 1,
        entrySheetOpen: false,
      })
    ).toBe(false);
  });

  it('covers all four maturity phases', () => {
    expect(MATURITY_INTRO_PHASES).toEqual([
      'collecting',
      'early_patterns',
      'provisional',
      'robust',
    ]);
  });
});
