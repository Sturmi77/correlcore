import { cleanup, fireEvent, render, screen } from '@testing-library/svelte';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { InsightHistoryItem } from '$lib/api/insights';
import InsightHistoryTimeline from './InsightHistoryTimeline.svelte';

vi.mock('svelte-i18n', async () => {
  const { readable } = await import('svelte/store');
  return {
    _: readable((key: string, options?: { values?: Record<string, unknown> }) => {
      if (key === 'insights.history.heading') return 'Timeline';
      if (key === 'insights.history.hint') return 'Past evaluations';
      if (key === 'insights.history.filter_aria') return 'Filter';
      if (key === 'insights.history.filter_all') return 'All';
      if (key === 'insights.history.filter_active') return 'Visible';
      if (key === 'insights.history.filter_dismissed') return 'Hidden';
      if (key === 'insights.history.badge_past') return 'Past evaluation';
      if (key === 'insights.history.badge_dismissed') return 'Hidden';
      if (key === 'insights.history.day_heading') return String(options?.values?.date ?? '');
      if (key === 'insights.history.empty') return 'No insight history yet.';
      if (key === 'insights.history.evolution')
        return `Seen ${options?.values?.count}× from ${options?.values?.first} to ${options?.values?.last}`;
      return key;
    }),
  };
});

vi.mock('./InsightCard.svelte', () => ({
  default: function MockInsightCard(
    anchor: Element | Comment,
    props: Record<string, unknown> = {}
  ) {
    const el = document.createElement('div');
    el.setAttribute('data-testid', 'insight-card-mock');
    const insight = props.insight as { id?: string } | undefined;
    el.textContent = insight?.id ?? 'card';
    anchor.parentNode?.insertBefore(el, anchor);
    return {
      $on() {
        return () => {};
      },
      $set() {},
      $destroy() {
        el.remove();
      },
    };
  },
}));

const item: InsightHistoryItem = {
  id: 'insight-1',
  user_id: 'user-1',
  insight_type: 'spearman',
  tier: 'developing',
  metric: 'mood_score',
  subject_type: 'metric',
  subject_id: null,
  subject_label: 'energy',
  effect_size: 0.4,
  confidence: 0.7,
  sample_n: 20,
  statement: 'Mood lines up with energy.',
  flags: {},
  payload: {},
  generated_for_date: '2026-05-14',
  generated_at: '2026-05-14T00:00:00Z',
  created_at: '2026-05-14T00:00:00Z',
  updated_at: '2026-05-14T00:00:00Z',
  visibility: 'active',
  subject_key: 'sk',
  first_seen_on: '2026-05-01',
  last_seen_on: '2026-05-14',
  observation_count: 3,
};

describe('InsightHistoryTimeline', () => {
  afterEach(() => {
    cleanup();
  });

  it('renders empty state', () => {
    render(InsightHistoryTimeline, { props: { items: [], status: 'all' } });
    expect(screen.getByText('No insight history yet.')).toBeTruthy();
  });

  it('groups items by date and shows past badge', () => {
    render(InsightHistoryTimeline, {
      props: { items: [item], status: 'all', total: 1 },
    });
    expect(screen.getByTestId('insight-history-timeline')).toBeTruthy();
    expect(screen.getByText('2026-05-14')).toBeTruthy();
    expect(screen.getByText('Past evaluation')).toBeTruthy();
    expect(screen.getByText('Seen 3× from 2026-05-01 to 2026-05-14')).toBeTruthy();
  });

  it('dispatches statusChange from filter tabs', async () => {
    const statusChange = vi.fn();
    render(InsightHistoryTimeline, {
      props: { items: [item], status: 'all', total: 1 },
      events: { statusChange },
    });
    await fireEvent.click(screen.getByRole('tab', { name: 'Hidden' }));
    expect(statusChange).toHaveBeenCalledWith(
      expect.objectContaining({ detail: { status: 'dismissed' } })
    );
  });
});
