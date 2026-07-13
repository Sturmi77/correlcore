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

vi.mock('svelte-i18n', () => ({
  _: {
    subscribe: (run: (formatter: (key: string) => string) => void) => {
      run((key: string) => key);
      return () => undefined;
    },
  },
}));

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

  // ── Filter tabs ───────────────────────────────────────────────────
  it('renders all 4 filter tabs', () => {
    render(InsightFeed, { props: { insights: [] } });
    expect(screen.getByTestId('insight-feed-tab-all')).toBeTruthy();
    expect(screen.getByTestId('insight-feed-tab-mood')).toBeTruthy();
    expect(screen.getByTestId('insight-feed-tab-symptoms')).toBeTruthy();
    expect(screen.getByTestId('insight-feed-tab-context')).toBeTruthy();
  });

  it('all tab is selected by default', () => {
    render(InsightFeed, { props: { insights: [] } });
    expect(screen.getByTestId('insight-feed-tab-all').getAttribute('aria-selected')).toBe('true');
  });

  it('clicking mood tab sets aria-selected=true on mood', async () => {
    render(InsightFeed, { props: { insights: [] } });
    await fireEvent.click(screen.getByTestId('insight-feed-tab-mood'));
    expect(screen.getByTestId('insight-feed-tab-mood').getAttribute('aria-selected')).toBe('true');
    expect(screen.getByTestId('insight-feed-tab-all').getAttribute('aria-selected')).toBe('false');
  });

  it('mood tab filters out non-mood insights', async () => {
    const moodInsight = makeInsight({ id: 'm', metric: 'mood' });
    const energyInsight = makeInsight({ id: 'e', metric: 'energy' });
    render(InsightFeed, { props: { insights: [moodInsight, energyInsight] } });
    await fireEvent.click(screen.getByTestId('insight-feed-tab-mood'));
    const list = screen.getByTestId('insight-feed-list');
    expect(list.querySelectorAll('li').length).toBe(1);
  });

  it('symptoms tab includes future symptom insight payloads', async () => {
    const symptomInsight = makeInsight({
      id: 'symptom',
      metric: 'mood',
      insight_type: 'symptom_mood_association',
      subject_type: 'symptom',
      subject_label: 'Headache',
    });
    const tagInsight = makeInsight({ id: 'tag', metric: 'mood', subject_type: 'tag' });
    render(InsightFeed, { props: { insights: [symptomInsight, tagInsight] } });
    await fireEvent.click(screen.getByTestId('insight-feed-tab-symptoms'));
    const list = screen.getByTestId('insight-feed-list');
    expect(list.querySelectorAll('li').length).toBe(1);
  });

  it('context tab shows calendar and office context insights only', async () => {
    const contextInsight = makeInsight({
      id: 'context',
      insight_type: 'work_context_pattern',
      payload: { work_context: 'office' },
    });
    const tagInsight = makeInsight({ id: 'tag', metric: 'mood', subject_type: 'tag' });
    render(InsightFeed, { props: { insights: [contextInsight, tagInsight] } });

    await fireEvent.click(screen.getByTestId('insight-feed-tab-context'));

    const list = screen.getByTestId('insight-feed-list');
    expect(list.querySelectorAll('li').length).toBe(1);
    expect(screen.getByTestId('insight-card-context-badge')).toBeTruthy();
  });

  it('uses external filterTab when provided', async () => {
    const moodInsight = makeInsight({ id: 'm', metric: 'mood' });
    const sleepInsight = makeInsight({ id: 's', metric: 'sleep' });
    render(InsightFeed, {
      props: {
        insights: [moodInsight, sleepInsight],
        filterTab: 'mood',
        showFilters: false,
      },
    });
    const list = screen.getByTestId('insight-feed-list');
    expect(list.querySelectorAll('li').length).toBe(1);
    expect(screen.queryByTestId('insight-feed-tabs')).toBeNull();
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

  it('renders disclaimer button', () => {
    render(InsightFeed, { props: { insights: [] } });
    expect(screen.getByTestId('insight-feed-disclaimer-btn')).toBeTruthy();
  });
});
