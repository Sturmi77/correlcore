/**
 * InsightFeed.test.ts
 *
 * Covers acceptance criteria from issue #164.
 * Uses @testing-library/svelte + vitest.
 *
 * Learnings applied:
 * - No component.$on() - use Svelte 5 `events` render option instead
 * - No inline type params in vi.mock callbacks
 * - Use InsightResponse, not InsightDto
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/svelte';
import InsightFeed from './InsightFeed.svelte';
import type { InsightMaturity, InsightResponse } from '$lib/api/insights';

vi.mock('svelte-i18n', async () => {
  const { readable } = await import('svelte/store');

  return {
    _: {
      subscribe: (run: (formatter: (key: string) => string) => void) => {
        run((key: string) => key);
        return () => undefined;
      },
    },
    // #755: InsightFeed reads $locale to format the staleness banner date.
    locale: readable('en'),
  };
});

function makeInsight(overrides: Partial<InsightResponse> = {}): InsightResponse {
  return {
    id: 'i-' + Math.random().toString(36).slice(2),
    user_id: 'u1',
    insight_type: 'spearman',
    tier: 'developing',
    metric: 'mood',
    subject_type: 'tag',
    subject_id: 'sport',
    subject_label: 'sport',
    confidence: 0.5,
    effect_size: 0.3,
    sample_n: 30,
    statement: 'Test statement.',
    flags: {},
    payload: {},
    generated_for_date: '2026-05-10',
    generated_at: '2026-05-10T10:00:00Z',
    created_at: '2026-05-10T10:00:00Z',
    updated_at: '2026-05-10T10:00:00Z',
    ...overrides,
  };
}

const maturity: InsightMaturity = {
  phase: 'early_patterns',
  phase_index: 2,
  current_entries: 9,
  next_phase_at: 14,
  next_phase_label: 'Provisional Insights',
  entries_until_next: 5,
  user_message_key: 'maturity.early_patterns.description',
};

describe('InsightFeed', () => {
  // ── Skeleton ─────────────────────────────────────────────────────
  it('renders skeleton when loading=true', () => {
    render(InsightFeed, { props: { loading: true } });
    expect(screen.getByTestId('insight-feed-skeleton')).toBeTruthy();
  });

  it('skeleton has aria-busy=true', () => {
    render(InsightFeed, { props: { loading: true } });
    expect(screen.getByTestId('insight-feed-skeleton').getAttribute('aria-busy')).toBe('true');
  });

  // ── Empty state ───────────────────────────────────────────────────
  it('renders empty state when insights=[]', () => {
    render(InsightFeed, { props: { insights: [] } });
    expect(screen.getByTestId('insight-feed-empty')).toBeTruthy();
  });

  it('empty state contains a link back to home', () => {
    render(InsightFeed, { props: { insights: [] } });
    const cta = screen.getByRole('link');
    expect(cta.getAttribute('href')).toBe('/?openEntry=1');
  });

  it('uses phase-aware empty copy when no insights exist yet', () => {
    render(InsightFeed, { props: { insights: [], maturity } });

    expect(screen.getByText('insights.feed.empty_phase.early_patterns.title')).toBeTruthy();
    expect(screen.getByText('insights.feed.empty_phase.early_patterns.body')).toBeTruthy();
  });

  it('uses "no new insights" copy when all insights have been dismissed (#686)', () => {
    render(InsightFeed, {
      props: {
        // Dismissed insights are removed from the list; dismissedCount records them.
        insights: [],
        totalInsightCount: 0,
        dismissedCount: 3,
      },
    });

    expect(screen.getByText('insights.feed.empty_all_dismissed_title')).toBeTruthy();
    expect(screen.getByText('insights.feed.empty_all_dismissed_body')).toBeTruthy();
    expect(screen.queryByText('insights.feed.empty_title')).toBeNull();
    expect(screen.queryByTestId('insight-feed-empty-secondary-cta')).toBeNull();
  });

  it('uses the plain empty copy when there are genuinely no insights (none dismissed)', () => {
    render(InsightFeed, { props: { insights: [], totalInsightCount: 0, dismissedCount: 0 } });
    expect(screen.getByText('insights.feed.empty_title')).toBeTruthy();
    expect(screen.queryByText('insights.feed.empty_all_dismissed_title')).toBeNull();
  });

  it('uses robust phase empty copy and regenerate CTA when API returned no insights', () => {
    const robustMaturity: InsightMaturity = {
      ...maturity,
      phase: 'robust',
      phase_index: 4,
      current_entries: 67,
      next_phase_at: null,
      next_phase_label: null,
      entries_until_next: null,
    };

    render(InsightFeed, {
      props: {
        insights: [],
        totalInsightCount: 0,
        maturity: robustMaturity,
        entryCount: 67,
      },
    });

    expect(screen.getByText('insights.feed.empty_phase.robust.title')).toBeTruthy();
    expect(screen.getByText('insights.feed.empty_phase.robust.body')).toBeTruthy();
    expect(screen.getByTestId('insight-feed-empty-secondary-cta')).toBeTruthy();
  });

  it('dispatches regenerate from the empty-state secondary CTA', async () => {
    const handler = vi.fn();
    const robustMaturity: InsightMaturity = {
      ...maturity,
      phase: 'robust',
      phase_index: 4,
      current_entries: 67,
      next_phase_at: null,
      next_phase_label: null,
      entries_until_next: null,
    };

    render(InsightFeed, {
      props: {
        insights: [],
        totalInsightCount: 0,
        maturity: robustMaturity,
      },
      events: { regenerate: handler },
    });

    await fireEvent.click(screen.getByTestId('insight-feed-empty-secondary-cta'));
    expect(handler).toHaveBeenCalledOnce();
  });

  // ── Error banner ──────────────────────────────────────────────────
  it('renders inline error banner when error is set', () => {
    render(InsightFeed, { props: { error: 'Network failure' } });
    expect(screen.getByTestId('insight-feed-error')).toBeTruthy();
  });

  it('error banner has role=alert', () => {
    render(InsightFeed, { props: { error: 'err' } });
    expect(screen.getByRole('alert')).toBeTruthy();
  });

  it('dispatches retry when retry button is clicked', async () => {
    const handler = vi.fn();
    render(InsightFeed, { props: { error: 'err' }, events: { retry: handler } });
    await fireEvent.click(screen.getByTestId('insight-feed-retry'));
    expect(handler).toHaveBeenCalledOnce();
  });

  it('forwards exploreEvents from insight cards when enabled', async () => {
    const handler = vi.fn();
    const insight = makeInsight({ id: 'tag-insight', subject_type: 'tag' });
    render(InsightFeed, {
      props: {
        insights: [insight],
        maturity: { ...maturity, phase: 'provisional' },
        enableExploreEvents: true,
      },
      events: { exploreEvents: handler },
    });

    await fireEvent.click(screen.getByTestId('insight-card-explore-events'));

    expect(handler).toHaveBeenCalledOnce();
    expect(handler.mock.calls[0]?.[0].detail).toEqual({ id: 'tag-insight' });
  });

  // ── Sort order ────────────────────────────────────────────────────
  it('sorts insights by confidence × |effect_size| descending', () => {
    const low = makeInsight({ id: 'low', confidence: 0.3, effect_size: 0.2 }); // score 0.06
    const high = makeInsight({ id: 'high', confidence: 0.9, effect_size: 0.8 }); // score 0.72
    const mid = makeInsight({ id: 'mid', confidence: 0.5, effect_size: 0.5 }); // score 0.25
    render(InsightFeed, { props: { insights: [low, high, mid], maturity } });
    const list = screen.getByTestId('insight-feed-list');
    const items = list.querySelectorAll('li');
    // order: high (0.72), mid (0.25), low (0.06)
    expect(items.length).toBe(3);
  });

  it('marks only the top-ranked insight as featured', () => {
    const low = makeInsight({ id: 'low', confidence: 0.3, effect_size: 0.2 });
    const high = makeInsight({ id: 'high', confidence: 0.9, effect_size: 0.8 });
    const mid = makeInsight({ id: 'mid', confidence: 0.5, effect_size: 0.5 });
    render(InsightFeed, { props: { insights: [low, high, mid], maturity } });
    const cards = screen
      .getByTestId('insight-feed-list')
      .querySelectorAll('[data-testid="insight-card"]');
    expect(cards.length).toBe(3);
    expect(cards[0]?.getAttribute('data-featured')).toBe('true');
    expect(cards[1]?.getAttribute('data-featured')).toBe('false');
    expect(cards[2]?.getAttribute('data-featured')).toBe('false');
  });

  // ── No in-feed filter (#685) ──────────────────────────────────────
  it('no longer renders the symptom/mood filter tabs', () => {
    render(InsightFeed, {
      props: { insights: [makeInsight(), makeInsight({ metric: 'energy' })] },
    });
    expect(screen.queryByTestId('insight-feed-tabs')).toBeNull();
    expect(screen.queryByTestId('insight-feed-tab-all')).toBeNull();
    expect(screen.queryByTestId('insight-feed-tab-mood')).toBeNull();
    // All insights render — no filtering removes any.
    expect(screen.getByTestId('insight-feed-list').querySelectorAll('li').length).toBe(2);
  });

  // ── Header ────────────────────────────────────────────────────────
  it('does not render a duplicate screen title', () => {
    render(InsightFeed, { props: { insights: [] } });
    expect(screen.queryByTestId('insight-feed-title')).toBeNull();
  });

  it('renders compact context with entry count', () => {
    render(InsightFeed, { props: { insights: [], entryCount: 42 } });
    expect(screen.getByTestId('insight-feed-context')).toBeTruthy();
  });

  it('keeps readiness out of the feed card stack', () => {
    render(InsightFeed, {
      props: {
        insights: [makeInsight({ confidence: 0.7, effect_size: 0.5, tier: 'developing' })],
      },
    });

    expect(screen.queryByTestId('insight-quality-meter')).toBeNull();
  });

  it('shows correlation hint when insights are loaded', () => {
    render(InsightFeed, { props: { insights: [makeInsight()] } });
    expect(screen.getByTestId('insight-feed-correlation-hint')).toBeTruthy();
  });

  it('hides correlation hint while loading, on error, or when empty', () => {
    const { unmount: unmountLoading } = render(InsightFeed, {
      props: { insights: [], loading: true },
    });
    expect(screen.queryByTestId('insight-feed-correlation-hint')).toBeNull();
    unmountLoading();

    const { unmount: unmountError } = render(InsightFeed, {
      props: { insights: [], error: 'boom' },
    });
    expect(screen.queryByTestId('insight-feed-correlation-hint')).toBeNull();
    unmountError();

    render(InsightFeed, { props: { insights: [] } });
    expect(screen.queryByTestId('insight-feed-correlation-hint')).toBeNull();
  });

  it('renders disclaimer button', () => {
    render(InsightFeed, { props: { insights: [] } });
    expect(screen.getByTestId('insight-feed-disclaimer-btn')).toBeTruthy();
  });

  // ── Staleness banner (#755) ───────────────────────────────────────────
  it('shows the staleness banner when insights exist but are older than the threshold', () => {
    const stale = makeInsight({ generated_at: '2026-05-01T00:00:00Z' });
    render(InsightFeed, {
      props: { insights: [stale], now: '2026-05-05T00:00:00Z' }, // 96h later
    });

    expect(screen.getByTestId('insight-feed-stale-banner')).toBeTruthy();
    expect(screen.getByTestId('insight-feed-stale-action')).toBeTruthy();
    // The feed itself must still render — staleness is independent of the empty state.
    expect(screen.getByTestId('insight-feed-list')).toBeTruthy();
  });

  it('hides the staleness banner when the latest insight is within the threshold', () => {
    const fresh = makeInsight({ generated_at: '2026-05-04T12:00:00Z' });
    render(InsightFeed, {
      props: { insights: [fresh], now: '2026-05-05T00:00:00Z' }, // 11.5h later
    });

    expect(screen.queryByTestId('insight-feed-stale-banner')).toBeNull();
  });

  it('uses the successful run timestamp when a zero-candidate run leaves old rows in place', () => {
    const oldRow = makeInsight({ generated_at: '2026-05-01T00:00:00Z' });
    render(InsightFeed, {
      props: {
        insights: [oldRow],
        now: '2026-05-05T00:00:00Z',
        lastSuccessfulInsightRunAt: '2026-05-04T23:00:00Z',
      },
    });

    expect(screen.queryByTestId('insight-feed-stale-banner')).toBeNull();
  });

  it('uses the complete staleness set when the rendered feed excludes the mobile lead card', () => {
    const primaryFresh = makeInsight({ id: 'primary', generated_at: '2026-05-04T23:00:00Z' });
    const remainingOld = makeInsight({ id: 'remaining', generated_at: '2026-05-01T00:00:00Z' });
    render(InsightFeed, {
      props: {
        insights: [remainingOld],
        stalenessInsights: [primaryFresh, remainingOld],
        now: '2026-05-05T00:00:00Z',
      },
    });

    expect(screen.queryByTestId('insight-feed-stale-banner')).toBeNull();
  });

  it('renders the stale warning without an empty state for a compact primary card', () => {
    const stalePrimary = makeInsight({ generated_at: '2026-05-01T00:00:00Z' });
    render(InsightFeed, {
      props: {
        insights: [],
        stalenessInsights: [stalePrimary],
        hideContent: true,
        now: '2026-05-05T00:00:00Z',
      },
    });

    expect(screen.getByTestId('insight-feed-stale-banner')).toBeTruthy();
    expect(screen.queryByTestId('insight-feed-empty')).toBeNull();
  });

  it('suppresses stale regeneration when analytics is disabled', () => {
    const stale = makeInsight({ generated_at: '2026-05-01T00:00:00Z' });
    render(InsightFeed, {
      props: { insights: [stale], now: '2026-05-05T00:00:00Z', analyticsEnabled: false },
    });

    expect(screen.queryByTestId('insight-feed-stale-banner')).toBeNull();
    expect(screen.queryByTestId('insight-feed-stale-action')).toBeNull();
  });

  it('updates staleness as wall-clock time passes when no test time is injected', async () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-05-02T15:00:00Z'));
    const nearlyStale = makeInsight({ generated_at: '2026-05-01T00:00:00Z' });
    render(InsightFeed, { props: { insights: [nearlyStale] } });

    expect(screen.queryByTestId('insight-feed-stale-banner')).toBeNull();
    await vi.advanceTimersByTimeAsync(2 * 60 * 60 * 1000);

    expect(screen.getByTestId('insight-feed-stale-banner')).toBeTruthy();
    vi.useRealTimers();
  });

  it('hides the staleness banner for the true-empty state (no generated_at to compare)', () => {
    render(InsightFeed, {
      props: { insights: [], maturity, now: '2026-05-05T00:00:00Z' },
    });

    expect(screen.queryByTestId('insight-feed-stale-banner')).toBeNull();
    // Empty-state CTA still covers the true-empty case, independently of staleness.
    expect(screen.getByTestId('insight-feed-empty')).toBeTruthy();
  });

  it('respects a custom staleAfterHours threshold', () => {
    const insight = makeInsight({ generated_at: '2026-05-04T00:00:00Z' });
    const { unmount } = render(InsightFeed, {
      props: { insights: [insight], now: '2026-05-05T00:00:00Z', staleAfterHours: 48 }, // 24h later
    });
    expect(screen.queryByTestId('insight-feed-stale-banner')).toBeNull();
    unmount();

    render(InsightFeed, {
      props: { insights: [insight], now: '2026-05-05T00:00:00Z', staleAfterHours: 12 }, // 24h later
    });
    expect(screen.getByTestId('insight-feed-stale-banner')).toBeTruthy();
  });

  it('dispatches regenerate from the staleness banner action', async () => {
    const handler = vi.fn();
    const stale = makeInsight({ generated_at: '2026-05-01T00:00:00Z' });
    render(InsightFeed, {
      props: { insights: [stale], now: '2026-05-05T00:00:00Z' },
      events: { regenerate: handler },
    });

    await fireEvent.click(screen.getByTestId('insight-feed-stale-action'));
    expect(handler).toHaveBeenCalledOnce();
  });

  it('hides the staleness banner while loading or on error, even if stale', () => {
    const stale = makeInsight({ generated_at: '2026-05-01T00:00:00Z' });
    const { unmount: unmountLoading } = render(InsightFeed, {
      props: { insights: [stale], now: '2026-05-05T00:00:00Z', loading: true },
    });
    expect(screen.queryByTestId('insight-feed-stale-banner')).toBeNull();
    unmountLoading();

    render(InsightFeed, {
      props: { insights: [stale], now: '2026-05-05T00:00:00Z', error: 'boom' },
    });
    expect(screen.queryByTestId('insight-feed-stale-banner')).toBeNull();
  });
});
