/**
 * InsightCard.test.ts
 *
 * Covers all acceptance criteria from issue #163.
 * Uses @testing-library/svelte + vitest.
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/svelte';
import InsightCard from './InsightCard.svelte';
import type { InsightMaturity, InsightResponse } from '$lib/api/insights';

vi.mock('svelte-i18n', async () => {
  const { readable } = await import('svelte/store');

  return {
    _: readable((key: string, options?: { values?: Record<string, unknown> }) => {
      if (key === 'home.confidence_scale.entry_count')
        return `Based on ${options?.values?.n} entries`;
      if (key === 'insights.card.sample_meta') return `Based on ${options?.values?.n} entries`;
      return key;
    }),
  };
});

// Minimal fixture that satisfies InsightResponse
const INSIGHT: InsightResponse = {
  id: 'test-001',
  user_id: 'u1',
  insight_type: 'spearman',
  tier: 'developing',
  metric: 'mood',
  subject_type: 'tag',
  subject_id: 'sport',
  subject_label: 'sport',
  confidence: 0.72,
  effect_size: 0.38,
  sample_n: 42,
  statement: 'On days you exercised, your mood tended to be higher.',
  flags: {},
  payload: {
    r_value: 0.612,
    rho_value: 0.598,
    p_value: 0.031,
    time_window_days: 60,
    tag_a: 'sport',
    tag_b: 'mood',
  },
  generated_for_date: '2026-05-10',
  generated_at: '2026-05-10T10:00:00Z',
  created_at: '2026-05-10T10:00:00Z',
  updated_at: '2026-05-12T08:00:00Z',
};

const NEGATIVE_INSIGHT: InsightResponse = {
  ...INSIGHT,
  id: 'test-002',
  effect_size: -0.42,
  statement: 'Higher stress correlates with lower mood in your data.',
  subject_id: 'stress',
  subject_label: 'stress',
  payload: { ...INSIGHT.payload, r_value: -0.551, tag_a: 'stress' },
};

const MATURITY: InsightMaturity = {
  phase: 'provisional',
  phase_index: 3,
  current_entries: 21,
  next_phase_at: 30,
  next_phase_label: 'Robust Insights',
  entries_until_next: 9,
  user_message_key: 'maturity.provisional.description',
};

describe('InsightCard', () => {
  // ── Collapsed (Level 1) ──────────────────────────────────────────
  it('renders statement in collapsed state', () => {
    render(InsightCard, { props: { insight: INSIGHT } });
    expect(screen.getByTestId('insight-card-statement').textContent).toContain(
      'On days you exercised'
    );
  });

  it('renders positive direction indicator (↗) for positive effect size', () => {
    render(InsightCard, { props: { insight: INSIGHT } });
    const dir = screen.getByTestId('insight-card-direction');
    expect(dir.textContent?.trim()).toBe('↗');
  });

  it('renders negative direction indicator (↘) for negative effect size', () => {
    render(InsightCard, { props: { insight: NEGATIVE_INSIGHT } });
    const dir = screen.getByTestId('insight-card-direction');
    expect(dir.textContent?.trim()).toBe('↘');
  });

  it('renders title as "metric -> subject" format', () => {
    render(InsightCard, { props: { insight: INSIGHT } });
    expect(screen.getByTestId('insight-card-title').textContent).toContain('mood → sport');
  });

  it('marks insights for inactive tags without hiding them', () => {
    render(InsightCard, { props: { insight: INSIGHT, inactiveTagIds: ['sport'] } });

    expect(screen.getByTestId('insight-card-title').textContent).toContain(
      'insights.card.inactive_tag_badge'
    );
    expect(screen.getByTestId('insight-card-meta').textContent).toContain(
      'insights.card.inactive_tag_hint'
    );
  });

  it('does NOT show raw percentage in collapsed state', () => {
    render(InsightCard, { props: { insight: INSIGHT } });
    expect(screen.queryByTestId('insight-confidence-score-percent')).toBeNull();
  });

  it('renders a maturity badge when maturity is provided', () => {
    render(InsightCard, { props: { insight: INSIGHT, maturity: MATURITY } });
    const badge = screen.getByTestId('insight-maturity-badge');

    expect(badge.getAttribute('data-phase')).toBe('provisional');
    expect(badge.textContent).toContain('maturity.badge.provisional');
  });

  it('renders disclaimer link', () => {
    render(InsightCard, { props: { insight: INSIGHT } });
    const link = screen.getByTestId('insight-card-disclaimer');
    expect(link).toBeTruthy();
    expect(link.tagName.toLowerCase()).toBe('a');
  });

  it('expand toggle has correct ARIA attributes in collapsed state', () => {
    render(InsightCard, { props: { insight: INSIGHT } });
    const toggle = screen.getByTestId('insight-card-toggle');
    expect(toggle.getAttribute('aria-expanded')).toBe('false');
  });

  // ── Expanding to Level 2 ─────────────────────────────────────────
  it('clicking expand toggle shows the chart container', async () => {
    render(InsightCard, { props: { insight: INSIGHT } });
    const toggle = screen.getByTestId('insight-card-toggle');
    await fireEvent.click(toggle);
    expect(screen.getByTestId('insight-card-chart')).toBeTruthy();
  });

  it('aria-expanded is true after expanding', async () => {
    render(InsightCard, { props: { insight: INSIGHT } });
    const toggle = screen.getByTestId('insight-card-toggle');
    await fireEvent.click(toggle);
    expect(toggle.getAttribute('aria-expanded')).toBe('true');
  });

  it('level 2 shows effect size when present', async () => {
    render(InsightCard, { props: { insight: INSIGHT } });
    await fireEvent.click(screen.getByTestId('insight-card-toggle'));
    expect(screen.getByTestId('insight-card-effect-size').textContent).toContain('0.380');
  });

  it('level 2 shows raw confidence float', async () => {
    render(InsightCard, { props: { insight: INSIGHT } });
    await fireEvent.click(screen.getByTestId('insight-card-toggle'));
    expect(screen.getByTestId('insight-card-confidence-raw').textContent).toContain('72');
  });

  // ── States ───────────────────────────────────────────────────────
  it('renders skeleton when loading=true', () => {
    render(InsightCard, { props: { loading: true } });
    expect(screen.getByTestId('insight-card-skeleton')).toBeTruthy();
  });

  it('renders error state with retry button when error is set', () => {
    render(InsightCard, { props: { error: 'Network failure' } });
    expect(screen.getByTestId('insight-card-error')).toBeTruthy();
    expect(screen.getByTestId('insight-card-retry')).toBeTruthy();
  });

  it('dispatches retry event when retry button is clicked', async () => {
    const handler = vi.fn();
    render(InsightCard, { props: { error: 'err' }, events: { retry: handler } });
    await fireEvent.click(screen.getByTestId('insight-card-retry'));
    expect(handler).toHaveBeenCalledOnce();
  });
});
