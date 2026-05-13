import { render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import HomeInsight from './HomeInsight.svelte';

vi.mock('svelte-i18n', async () => {
  const { readable } = await import('svelte/store');

  return {
    _: readable((key: string) => key),
  };
});

const insight = {
  id: 'insight-1',
  user_id: 'user-1',
  insight_type: 'weekday_pattern' as const,
  tier: 'early' as const,
  metric: 'mood_score',
  subject_type: 'weekday',
  subject_id: null,
  subject_label: 'Monday',
  effect_size: 0.4,
  confidence: 0.57,
  sample_n: 9,
  statement: 'Mondays currently line up with higher mood than your overall average.',
  flags: { causal_claim: false },
  payload: {},
  generated_for_date: '2026-05-12',
  generated_at: '2026-05-12T03:00:00Z',
  created_at: '2026-05-12T03:00:00Z',
  updated_at: '2026-05-12T03:00:00Z',
};

describe('HomeInsight', () => {
  it('renders a neutral latest insight preview', () => {
    render(HomeInsight, { props: { insight, loading: false } });

    expect(screen.getByText('home.insight.heading')).toBeTruthy();
    const badge = screen.getByText('home.insight.tier.early');
    expect(badge).toBeTruthy();
    expect(badge.getAttribute('title')).toBe('home.insight.tier_help.early');
    expect(badge.getAttribute('data-tier')).toBe('early');
    expect(screen.getByText(insight.statement)).toBeTruthy();
    expect(screen.getByText('57%')).toBeTruthy();
    expect(screen.getByText('9')).toBeTruthy();
    expect(screen.getByText('disclaimer.medical')).toBeTruthy();
    expect(screen.getByText('home.insight.more').getAttribute('href')).toBe('/insights');
  });

  it('renders empty and loading states', () => {
    const loading = render(HomeInsight, { props: { insight: null, loading: true } });
    expect(loading.container.querySelector('.home-insight__line--wide')).toBeTruthy();
    loading.unmount();

    render(HomeInsight, { props: { insight: null, loading: false } });
    expect(screen.getByText('home.insight.empty')).toBeTruthy();
    expect(screen.getByText('home.insight.empty_hint')).toBeTruthy();
  });
});
