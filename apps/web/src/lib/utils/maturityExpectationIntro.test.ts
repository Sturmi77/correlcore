import { describe, expect, it } from 'vitest';
import {
  MATURITY_INTRO_PHASES,
  shouldShowMaturityExpectationIntro,
} from './maturityExpectationIntro';

const prefs = {
  user_id: 'u1',
  analytics_enabled: true,
  digest_enabled: true,
  onboarding_retro_completed: true,
  onboarding_profile_completed: true,
  onboarding_maturity_intro_seen: false,
  dismissed_insight_keys: [],
  reached_milestone_keys: [],
  last_seen_insight_at: null,
  created_at: '',
  updated_at: '',
};

describe('shouldShowMaturityExpectationIntro', () => {
  it('shows after the first entry when not yet seen', () => {
    expect(
      shouldShowMaturityExpectationIntro({
        preferences: prefs,
        entryCount: 1,
        entrySheetOpen: false,
      })
    ).toBe(true);
  });

  it('hides while the entry sheet is open', () => {
    expect(
      shouldShowMaturityExpectationIntro({
        preferences: prefs,
        entryCount: 1,
        entrySheetOpen: true,
      })
    ).toBe(false);
  });

  it('hides with zero entries or after dismiss', () => {
    expect(
      shouldShowMaturityExpectationIntro({
        preferences: prefs,
        entryCount: 0,
        entrySheetOpen: false,
      })
    ).toBe(false);
    expect(
      shouldShowMaturityExpectationIntro({
        preferences: { ...prefs, onboarding_maturity_intro_seen: true },
        entryCount: 3,
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
