import { describe, expect, it } from 'vitest';
import type { InsightResponse } from '$lib/api/insights';
import type { UserPreferencesResponse } from '$lib/api/preferences';
import {
  maxInsightGeneratedAt,
  selectNewInsightsSinceLastSeen,
  shouldShowNewInsightsModal,
} from './newInsightsModal';

const prefs = (overrides: Partial<UserPreferencesResponse> = {}): UserPreferencesResponse => ({
  user_id: 'u1',
  analytics_enabled: true,
  digest_enabled: false,
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

const insight = (overrides: Partial<InsightResponse> = {}): InsightResponse =>
  ({
    id: 'i1',
    user_id: 'u1',
    insight_type: 'pointbiserial',
    tier: 'developing',
    metric: 'mood_score',
    subject_type: 'tag',
    subject_id: 't1',
    subject_label: 'Walk',
    effect_size: 0.4,
    confidence: 0.7,
    sample_n: 20,
    statement: 'Walks track with mood.',
    flags: {},
    payload: {},
    generated_for_date: '2026-09-07',
    generated_at: '2026-09-07T03:00:00Z',
    created_at: '2026-09-07T03:00:00Z',
    updated_at: '2026-09-07T03:00:00Z',
    ...overrides,
  }) as InsightResponse;

describe('selectNewInsightsSinceLastSeen', () => {
  it('returns insights newer than last seen, ranked', () => {
    const rows = [
      insight({ id: 'old', generated_at: '2026-09-01T03:00:00Z', confidence: 0.9 }),
      insight({
        id: 'new-weak',
        generated_at: '2026-09-07T03:00:00Z',
        confidence: 0.4,
        effect_size: 0.2,
      }),
      insight({
        id: 'new-strong',
        generated_at: '2026-09-07T04:00:00Z',
        confidence: 0.8,
        effect_size: 0.5,
      }),
    ];
    const selected = selectNewInsightsSinceLastSeen(rows, '2026-09-06T03:00:00Z');
    expect(selected.map((r) => r.id)).toEqual(['new-strong', 'new-weak']);
  });

  it('excludes dismissed ids', () => {
    const rows = [insight({ id: 'a' }), insight({ id: 'b', generated_at: '2026-09-07T04:00:00Z' })];
    const selected = selectNewInsightsSinceLastSeen(rows, null, { dismissedIds: ['a'] });
    expect(selected.map((r) => r.id)).toEqual(['b']);
  });
});

describe('shouldShowNewInsightsModal', () => {
  it('shows when there are unseen insights', () => {
    const decision = shouldShowNewInsightsModal({
      preferences: prefs(),
      insights: [insight()],
    });
    expect(decision.show).toBe(true);
    expect(decision.candidates).toHaveLength(1);
  });

  it('does not show when already seen', () => {
    const decision = shouldShowNewInsightsModal({
      preferences: prefs({ last_seen_insight_at: '2026-09-07T03:00:00Z' }),
      insights: [insight()],
    });
    expect(decision.show).toBe(false);
  });

  it('yields to digest modal and day gate', () => {
    expect(
      shouldShowNewInsightsModal({
        preferences: prefs(),
        insights: [insight()],
        digestModalOpen: true,
      }).show
    ).toBe(false);
    expect(
      shouldShowNewInsightsModal({
        preferences: prefs(),
        insights: [insight()],
        alreadyShownToday: true,
      }).show
    ).toBe(false);
  });

  it('does not show when analytics disabled', () => {
    expect(
      shouldShowNewInsightsModal({
        preferences: prefs({ analytics_enabled: false }),
        insights: [insight()],
      }).show
    ).toBe(false);
  });
});

describe('maxInsightGeneratedAt', () => {
  it('returns the newest generated_at', () => {
    expect(
      maxInsightGeneratedAt([
        insight({ generated_at: '2026-09-01T00:00:00Z' }),
        insight({ generated_at: '2026-09-07T05:00:00Z' }),
      ])
    ).toBe('2026-09-07T05:00:00Z');
  });
});
