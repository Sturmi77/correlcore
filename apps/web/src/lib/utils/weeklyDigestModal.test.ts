import { describe, expect, it } from 'vitest';
import { shouldShowWeeklyDigestModal } from './weeklyDigestModal';
import type { UserPreferencesResponse } from '$lib/api/preferences';
import type { InsightDigestResponse } from '$lib/api/insights';

const prefs = (overrides: Partial<UserPreferencesResponse> = {}): UserPreferencesResponse => ({
  user_id: 'u1',
  analytics_enabled: true,
  digest_enabled: true,
  onboarding_retro_completed: false,
  onboarding_profile_completed: false,
  onboarding_maturity_intro_seen: false,
  cycle_tracking_enabled: true,
  dismissed_insight_keys: [],
  reached_milestone_keys: [],
  last_seen_insight_at: null,
  last_seen_digest_at: null,
  created_at: '',
  updated_at: '',
  ...overrides,
});

const digest = (overrides: Partial<InsightDigestResponse> = {}): InsightDigestResponse => ({
  week_start: '2026-08-10',
  week_end: '2026-08-16',
  insight_count: 3,
  insights: [
    {
      id: 'a',
      insight_type: 'tag_mood',
      metric: 'm',
      effect_size: 0.4,
      confidence: 0.8,
      statement: 's',
    },
  ],
  push_title: 't',
  push_body: 'b',
  generated_at: '2026-08-16T03:00:00Z',
  ...overrides,
});

describe('shouldShowWeeklyDigestModal', () => {
  it('shows a fresh stored digest never seen before', () => {
    expect(shouldShowWeeklyDigestModal({ preferences: prefs(), digest: digest() })).toBe(true);
  });

  it('shows when the digest is newer than last seen', () => {
    expect(
      shouldShowWeeklyDigestModal({
        preferences: prefs({ last_seen_digest_at: '2026-08-09T03:00:00Z' }),
        digest: digest(),
      })
    ).toBe(true);
  });

  it('does not show when the digest was already seen (same timestamp)', () => {
    expect(
      shouldShowWeeklyDigestModal({
        preferences: prefs({ last_seen_digest_at: '2026-08-16T03:00:00Z' }),
        digest: digest(),
      })
    ).toBe(false);
  });

  it('does not show when last seen is newer than the digest', () => {
    expect(
      shouldShowWeeklyDigestModal({
        preferences: prefs({ last_seen_digest_at: '2026-08-20T03:00:00Z' }),
        digest: digest(),
      })
    ).toBe(false);
  });

  it('does not show for the recompute fallback (generated_at null)', () => {
    expect(
      shouldShowWeeklyDigestModal({ preferences: prefs(), digest: digest({ generated_at: null }) })
    ).toBe(false);
  });

  it('does not show when the user opted out', () => {
    expect(
      shouldShowWeeklyDigestModal({
        preferences: prefs({ digest_enabled: false }),
        digest: digest(),
      })
    ).toBe(false);
  });

  it('does not show when the digest has no insights', () => {
    expect(
      shouldShowWeeklyDigestModal({
        preferences: prefs(),
        digest: digest({ insights: [], insight_count: 0 }),
      })
    ).toBe(false);
  });

  it('yields to an open entry/onboarding sheet', () => {
    expect(
      shouldShowWeeklyDigestModal({
        preferences: prefs(),
        digest: digest(),
        blockingSheetOpen: true,
      })
    ).toBe(false);
  });

  it('does not show without preferences or digest', () => {
    expect(shouldShowWeeklyDigestModal({ preferences: null, digest: digest() })).toBe(false);
    expect(shouldShowWeeklyDigestModal({ preferences: prefs(), digest: null })).toBe(false);
  });
});
