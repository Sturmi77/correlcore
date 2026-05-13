import { render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import WeekdayPatternChart from './WeekdayPatternChart.svelte';

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

describe('WeekdayPatternChart', () => {
  it('renders weekday mood averages and early signal copy', () => {
    render(WeekdayPatternChart, { props: { insight } });

    expect(screen.getByTestId('weekday-pattern-chart')).toBeTruthy();
    expect(screen.getByText('home.weekday_pattern.heading')).toBeTruthy();
    expect(screen.getByText('home.weekday_pattern.early_signal')).toBeTruthy();
    expect(screen.getByText('5.0')).toBeTruthy();
    expect(screen.getByText(insight.statement)).toBeTruthy();
  });
});
