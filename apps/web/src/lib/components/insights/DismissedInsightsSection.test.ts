import { cleanup, fireEvent, render, screen } from '@testing-library/svelte';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { InsightResponse } from '$lib/api/insights';
import DismissedInsightsSection from './DismissedInsightsSection.svelte';

vi.mock('svelte-i18n', async () => {
  const { readable } = await import('svelte/store');
  return {
    _: readable((key: string, options?: { values?: Record<string, unknown> }) => {
      if (key === 'insights.dismissed.heading') return 'Hidden insights';
      if (key === 'insights.dismissed.hint') return 'Hidden from your feed';
      if (key === 'insights.dismissed.undo') return 'Show again';
      if (key === 'insights.dismissed.undo_aria')
        return `Show insight "${options?.values?.title ?? ''}" again`;
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
    const insight = props.insight as InsightResponse | undefined;
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

const insight = {
  id: 'insight-hidden',
  user_id: 'user-1',
  insight_type: 'spearman' as const,
  tier: 'developing' as const,
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
} satisfies InsightResponse;

describe('DismissedInsightsSection', () => {
  afterEach(() => {
    cleanup();
  });

  it('renders nothing when empty', () => {
    render(DismissedInsightsSection, { props: { insights: [] } });
    expect(screen.queryByTestId('dismissed-insights-section')).toBeNull();
  });

  it('renders hidden insights and dispatches undismiss', async () => {
    const undismiss = vi.fn();
    render(DismissedInsightsSection, {
      props: {
        items: [{ dismissalId: 'dismissal-1', insight }],
      },
      events: { undismiss },
    });

    expect(screen.getByTestId('dismissed-insights-section')).toBeTruthy();
    expect(screen.getByText('Hidden insights')).toBeTruthy();
    await fireEvent.click(screen.getByTestId('dismissed-insight-undo'));
    expect(undismiss).toHaveBeenCalledOnce();
    expect(undismiss.mock.calls[0]?.[0].detail).toEqual({
      id: 'insight-hidden',
      dismissalId: 'dismissal-1',
    });
  });
});
