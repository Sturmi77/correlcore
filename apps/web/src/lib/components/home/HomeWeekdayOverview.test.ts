import { render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import HomeWeekdayOverview from './HomeWeekdayOverview.svelte';

vi.mock('svelte-i18n', async () => {
  const { readable } = await import('svelte/store');

  return {
    _: readable((key: string) => key),
  };
});

const weekdayInsight = {
  id: 'insight-weekday',
  user_id: 'user-1',
  insight_type: 'weekday_pattern' as const,
  tier: 'early' as const,
  metric: 'mood_score',
  subject_type: 'weekday',
  subject_id: null,
  subject_label: 'Friday',
  effect_size: 0.6,
  confidence: 0.3,
  sample_n: 7,
  statement: 'Fridays currently line up with higher mood than your overall average.',
  flags: { causal_claim: false, early_pattern: true },
  payload: {
    weekday_mood_avgs: {
      '0': 2,
      '1': 3,
      '2': 3,
      '3': 4,
      '4': 5,
      '5': 4,
      '6': 3,
    },
  },
  generated_for_date: '2026-05-12',
  generated_at: '2026-05-12T03:00:00Z',
  created_at: '2026-05-12T03:00:00Z',
  updated_at: '2026-05-12T03:00:00Z',
};

describe('HomeWeekdayOverview', () => {
  it('renders seven weekday columns with mood and findings', () => {
    render(HomeWeekdayOverview, {
      props: {
        weekdayInsight,
        insights: [
          weekdayInsight,
          {
            ...weekdayInsight,
            id: 'insight-tag',
            insight_type: 'pointbiserial',
            subject_type: 'tag',
            subject_label: 'Running',
            flags: { weekday_confounded: true },
            payload: { weekday: 1 },
          },
        ],
      },
    });

    expect(screen.getByTestId('home-weekday-overview')).toBeTruthy();
    expect(screen.getByText('home.weekday_overview.heading')).toBeTruthy();
    expect(screen.getByText('5.0')).toBeTruthy();
    expect(screen.getByText('Running')).toBeTruthy();
  });
});
