/**
 * Home zone composition tests (M3.5 Sprint 4).
 *
 * Verifies the three-zone layout renders CTA + insight states without
 * loading the full +page route (auth/layout dependencies).
 */

import { render, screen } from '@testing-library/svelte';
import { readable } from 'svelte/store';
import { describe, expect, it, vi } from 'vitest';
import HomeTodayContext from '$lib/components/home/HomeTodayContext.svelte';
import InsightCard from '$lib/components/insights/InsightCard.svelte';
import type { Insight } from '$lib/api/insights';

vi.mock('svelte-i18n', async () => {
  const { readable: r } = await import('svelte/store');
  return {
    _: r((key: string) => key),
    locale: r('en'),
  };
});

const insight: Insight = {
  id: 'insight-1',
  user_id: 'user-1',
  insight_type: 'spearman',
  tier: 'developing',
  metric: 'energy_mood',
  subject_type: 'metric',
  subject_id: null,
  subject_label: 'mood_score',
  effect_size: 0.42,
  confidence: 0.61,
  sample_n: 18,
  statement: 'Energy tends to be higher when mood is higher.',
  flags: { causal_claim: false },
  payload: {},
  generated_for_date: '2026-05-15',
  generated_at: '2026-05-15T03:00:00Z',
  created_at: '2026-05-15T03:00:00Z',
  updated_at: '2026-05-15T03:00:00Z',
};

describe('Home zone building blocks', () => {
  it('shows CTA-related empty state in today context', () => {
    render(HomeTodayContext, {
      props: { todayIso: '2026-05-15', todayEntry: null, loading: false },
    });
    expect(screen.getByTestId('home-today-status')).toBeTruthy();
  });

  it('renders insight card without blocking on error state', () => {
    render(InsightCard, {
      props: { insight: null, loading: false, error: 'Failed to load' },
    });
    expect(screen.getByTestId('insight-card-error')).toBeTruthy();
  });

  it('renders insight card when data is present', () => {
    render(InsightCard, {
      props: { insight, loading: false, error: '' },
    });
    expect(screen.getByText(insight.statement)).toBeTruthy();
  });
});
