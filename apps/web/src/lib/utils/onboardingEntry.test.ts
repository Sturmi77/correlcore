import { describe, expect, it } from 'vitest';
import {
  ONBOARDING_SUMMARY_SKIP_MAX_TAGS,
  shouldShowOnboardingTags,
  shouldSkipOnboardingSummary,
} from './onboardingEntry';

describe('onboardingEntry', () => {
  it('enables onboarding tags for new users without completed onboarding', () => {
    expect(
      shouldShowOnboardingTags(
        {
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
        },
        0
      )
    ).toBe(true);
  });

  it('disables onboarding tags after onboarding or when entries exist', () => {
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
    expect(shouldShowOnboardingTags({ ...prefs, onboarding_retro_completed: true }, 0)).toBe(false);
    expect(shouldShowOnboardingTags(prefs, 2)).toBe(false);
  });

  it('skips summary for at most three tags', () => {
    expect(ONBOARDING_SUMMARY_SKIP_MAX_TAGS).toBe(3);
    expect(shouldSkipOnboardingSummary(0)).toBe(true);
    expect(shouldSkipOnboardingSummary(3)).toBe(true);
    expect(shouldSkipOnboardingSummary(4)).toBe(false);
  });
});
