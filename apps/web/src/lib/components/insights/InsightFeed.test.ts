/**
 * InsightFeed.test.ts
 *
 * Covers acceptance criteria from issue #164.
 * Uses @testing-library/svelte + vitest.
 *
 * Learnings applied:
 * - No component.$on() — use container.addEventListener instead
 * - No inline type params in vi.mock callbacks — use `any` with eslint-disable
 * - Use InsightResponse, not InsightDto
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/svelte';
import InsightFeed from './InsightFeed.svelte';
import type { InsightResponse } from '$lib/api/insights';

vi.mock('svelte-i18n', () => ({
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  _: {
    subscribe: (run: any) => {
      run((v: any) => v);
      return () => {};
    },
  },
}));

vi.mock('./InsightCard.svelte', () => ({
  default: { render: () => ({ html: '<div data-testid="insight-card-mock"></div>' }) },
}));

vi.mock('./CorrelationDisclaimer.svelte', () => ({
  default: { render: () => ({ html: '' }) },
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
    expect(cta.getAttribute('href')).toBe('/');
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
    const { container } = render(InsightFeed, { props: { error: 'err' } });
    const handler = vi.fn();
    container.addEventListener('retry', handler);
    await fireEvent.click(screen.getByTestId('insight-feed-retry'));
    expect(handler).toHaveBeenCalledOnce();
  });

  // ── Sort order ────────────────────────────────────────────────────
  it('sorts insights by confidence × |effect_size| descending', () => {
    const low = makeInsight({ id: 'low', confidence: 0.3, effect_size: 0.2 }); // score 0.06
    const high = makeInsight({ id: 'high', confidence: 0.9, effect_size: 0.8 }); // score 0.72
    const mid = makeInsight({ id: 'mid', confidence: 0.5, effect_size: 0.5 }); // score 0.25
    render(InsightFeed, { props: { insights: [low, high, mid] } });
    const list = screen.getByTestId('insight-feed-list');
    const items = list.querySelectorAll('li');
    // order: high (0.72), mid (0.25), low (0.06)
    expect(items.length).toBe(3);
  });

  // ── Filter tabs ───────────────────────────────────────────────────
  it('renders all 4 filter tabs', () => {
    render(InsightFeed, { props: { insights: [] } });
    expect(screen.getByTestId('insight-feed-tab-all')).toBeTruthy();
    expect(screen.getByTestId('insight-feed-tab-mood')).toBeTruthy();
    expect(screen.getByTestId('insight-feed-tab-symptoms')).toBeTruthy();
    expect(screen.getByTestId('insight-feed-tab-sleep')).toBeTruthy();
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
    const sleepInsight = makeInsight({ id: 's', metric: 'sleep' });
    render(InsightFeed, { props: { insights: [moodInsight, sleepInsight] } });
    await fireEvent.click(screen.getByTestId('insight-feed-tab-mood'));
    const list = screen.getByTestId('insight-feed-list');
    expect(list.querySelectorAll('li').length).toBe(1);
  });

  it('sleep tab shows empty state when no sleep insights exist', async () => {
    const moodInsight = makeInsight({ metric: 'mood' });
    render(InsightFeed, { props: { insights: [moodInsight] } });
    await fireEvent.click(screen.getByTestId('insight-feed-tab-sleep'));
    expect(screen.getByTestId('insight-feed-empty')).toBeTruthy();
  });

  // ── Header ────────────────────────────────────────────────────────
  it('renders feed title', () => {
    render(InsightFeed, { props: { insights: [] } });
    expect(screen.getByTestId('insight-feed-title')).toBeTruthy();
  });

  it('renders subtitle with entry count', () => {
    render(InsightFeed, { props: { insights: [], entryCount: 42 } });
    expect(screen.getByTestId('insight-feed-subtitle')).toBeTruthy();
  });

  it('renders disclaimer button', () => {
    render(InsightFeed, { props: { insights: [] } });
    expect(screen.getByTestId('insight-feed-disclaimer-btn')).toBeTruthy();
  });
});
