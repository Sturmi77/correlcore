/**
 * InsightStore tests — Issue #167 (M3.1).
 *
 * Covers:
 *  - Store initialises with loading:false, empty insights
 *  - loadInsights() transitions to loaded state
 *  - latest is correctly derived (highest confidence × |effect_size|)
 *  - dismiss() updates dismissedIds and recomputes latest
 *  - API error does NOT throw — only sets error string
 *  - Home CTA unaffected (error state is isolated)
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { get } from 'svelte/store';

// ─── Mock API modules ─────────────────────────────────────────────────────────

vi.mock('$lib/api/insights', () => ({
  listLatestInsights: vi.fn(),
}));

vi.mock('$lib/api/preferences', () => ({
  fetchUserPreferences: vi.fn().mockResolvedValue({ dismissed_insight_keys: [] }),
  updateUserPreferences: vi.fn().mockResolvedValue({}),
}));

import { listLatestInsights } from '$lib/api/insights';
import type { InsightResponse } from '$lib/api/insights';
import { updateUserPreferences } from '$lib/api/preferences';
import {
  insightStore,
  rankedInsights,
  loadInsights,
  dismissInsight,
  resetInsightStore,
} from './insights';
import { devForceVisualizationsControl, devMode, devPhase } from './devMode';

// ─── Fixtures ─────────────────────────────────────────────────────────────────

const makeInsight = (
  overrides: Partial<{
    id: string;
    confidence: number | null;
    effect_size: number | null;
  }> = {}
) => ({
  id: 'insight-1',
  user_id: 'user-1',
  insight_type: 'pointbiserial' as const,
  tier: 'robust' as const,
  metric: 'mood_score',
  subject_type: 'tag',
  subject_id: 'tag-1',
  subject_label: 'Sport',
  effect_size: 0.42,
  confidence: 0.8,
  sample_n: 45,
  statement: 'Sport appears to be associated with higher mood scores.',
  flags: {},
  payload: {},
  generated_for_date: '2026-05-14',
  generated_at: '2026-05-14T00:00:00Z',
  created_at: '2026-05-14T00:00:00Z',
  updated_at: '2026-05-14T00:00:00Z',
  ...overrides,
});

const insightMaturity = {
  phase: 'provisional' as const,
  phase_index: 3 as const,
  current_entries: 18,
  next_phase_at: 30,
  next_phase_label: 'Robust Insights',
  entries_until_next: 12,
  user_message_key: 'maturity.provisional.description',
};

const insightList = (insights: InsightResponse[]) => ({
  insight_maturity: insightMaturity,
  insights,
});

// ─── Tests ────────────────────────────────────────────────────────────────────

beforeEach(() => {
  devMode.set(false);
  resetInsightStore();
  vi.clearAllMocks();
});

describe('insightStore — initial state', () => {
  it('initialises with loading:false and empty insights', () => {
    const state = get(insightStore);
    expect(state.loading).toBe(false);
    expect(state.insights).toEqual([]);
    expect(state.insightMaturity).toBeNull();
    expect(state.latest).toBeNull();
    expect(state.error).toBeNull();
    expect(state.dismissedIds).toEqual([]);
  });
});

describe('loadInsights()', () => {
  it('populates insights and derives latest on success', async () => {
    const insight = makeInsight();
    vi.mocked(listLatestInsights).mockResolvedValue(insightList([insight]));

    await loadInsights();

    const state = get(insightStore);
    expect(state.loading).toBe(false);
    expect(state.error).toBeNull();
    expect(state.insights).toHaveLength(1);
    expect(state.insightMaturity?.phase).toBe('provisional');
    expect(state.latest?.id).toBe('insight-1');
  });

  it('sets error string on API failure — does NOT throw', async () => {
    vi.mocked(listLatestInsights).mockRejectedValue(new Error('Network error'));

    // Must not throw
    await expect(loadInsights()).resolves.toBeUndefined();

    const state = get(insightStore);
    expect(state.loading).toBe(false);
    expect(state.error).toBe('Network error');
    // Insights list stays empty (or keeps prior value) — not corrupted
    expect(Array.isArray(state.insights)).toBe(true);
  });

  it('correctly picks latest as highest confidence × |effect_size|', async () => {
    const weak = makeInsight({ id: 'weak', confidence: 0.3, effect_size: 0.1 });
    const strong = makeInsight({ id: 'strong', confidence: 0.9, effect_size: 0.7 });
    const medium = makeInsight({ id: 'medium', confidence: 0.5, effect_size: 0.5 });
    vi.mocked(listLatestInsights).mockResolvedValue(insightList([weak, medium, strong]));

    await loadInsights();

    const state = get(insightStore);
    // strong: 0.9 × 0.7 = 0.63  >  medium: 0.25  >  weak: 0.03
    expect(state.latest?.id).toBe('strong');
  });

  it('latest is null when all insights are dismissed', async () => {
    const insight = makeInsight({ id: 'solo' });
    vi.mocked(listLatestInsights).mockResolvedValue(insightList([insight]));
    await loadInsights();

    await dismissInsight('solo');

    const state = get(insightStore);
    expect(state.latest).toBeNull();
  });

  it('loads the selected dev phase fixture when force visualizations are enabled', async () => {
    devMode.set(true);
    devForceVisualizationsControl.set(true);
    devPhase.setPreset('collecting');

    await loadInsights();

    const state = get(insightStore);
    expect(vi.mocked(listLatestInsights)).not.toHaveBeenCalled();
    expect(state.insightMaturity?.phase).toBe('collecting');
    expect(state.insights).toEqual([]);
  });
});

describe('dismissInsight()', () => {
  it('adds id to dismissedIds and recomputes latest', async () => {
    const a = makeInsight({ id: 'a', confidence: 0.9, effect_size: 0.7 });
    const b = makeInsight({ id: 'b', confidence: 0.6, effect_size: 0.5 });
    vi.mocked(listLatestInsights).mockResolvedValue(insightList([a, b]));
    await loadInsights();

    await dismissInsight('a');

    const state = get(insightStore);
    expect(state.dismissedIds).toContain('a');
    // b is now latest
    expect(state.latest?.id).toBe('b');
  });

  it('is idempotent — double dismiss does not duplicate id', async () => {
    const insight = makeInsight({ id: 'dup' });
    vi.mocked(listLatestInsights).mockResolvedValue(insightList([insight]));
    await loadInsights();

    await dismissInsight('dup');
    await dismissInsight('dup');

    const state = get(insightStore);
    expect(state.dismissedIds.filter((id) => id === 'dup')).toHaveLength(1);
  });

  it('fires PATCH /user/preferences best-effort on dismiss', async () => {
    const insight = makeInsight({ id: 'pref-test' });
    vi.mocked(listLatestInsights).mockResolvedValue(insightList([insight]));
    await loadInsights();

    await dismissInsight('pref-test');

    expect(vi.mocked(updateUserPreferences)).toHaveBeenCalledWith({
      dismissed_insight_keys: ['pref-test'],
    });
  });

  it('does NOT throw when preferences PATCH fails', async () => {
    const insight = makeInsight({ id: 'prefs-fail' });
    vi.mocked(listLatestInsights).mockResolvedValue(insightList([insight]));
    vi.mocked(updateUserPreferences).mockRejectedValue(new Error('Prefs error'));
    await loadInsights();

    // Must not throw even when the PATCH fails
    await expect(dismissInsight('prefs-fail')).resolves.toBeUndefined();
  });
});

describe('rankedInsights derived store', () => {
  it('sorts by confidence × |effect_size| descending', async () => {
    const low = makeInsight({ id: 'low', confidence: 0.2, effect_size: 0.1 });
    const high = makeInsight({ id: 'high', confidence: 0.9, effect_size: 0.8 });
    const mid = makeInsight({ id: 'mid', confidence: 0.5, effect_size: 0.4 });
    vi.mocked(listLatestInsights).mockResolvedValue(insightList([low, mid, high]));
    await loadInsights();

    const ranked = get(rankedInsights);
    expect(ranked.map((i) => i.id)).toEqual(['high', 'mid', 'low']);
  });

  it('excludes dismissed ids from ranked list', async () => {
    const a = makeInsight({ id: 'a', confidence: 0.9, effect_size: 0.8 });
    const b = makeInsight({ id: 'b', confidence: 0.5, effect_size: 0.4 });
    vi.mocked(listLatestInsights).mockResolvedValue(insightList([a, b]));
    await loadInsights();

    await dismissInsight('a');

    const ranked = get(rankedInsights);
    expect(ranked.map((i) => i.id)).toEqual(['b']);
  });
});
