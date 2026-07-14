import { render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import HabitDetailBody from './HabitDetailBody.svelte';

vi.mock('svelte-i18n', async () => {
  const { readable } = await import('svelte/store');
  return {
    _: readable((key: string) => {
      if (key === 'habits.insufficient_data') return 'Not enough data yet';
      if (key === 'habits.adherence_meter') return 'Adherence';
      if (key === 'habits.days_tracked') return 'Tracked days';
      if (key === 'habits.target_days') return 'Target days';
      if (key === 'habits.target_frequency') return 'Weekly target';
      if (key === 'habits.goal.label') return 'Goal';
      if (key === 'habits.goal.build') return '3 of 3 target days';
      if (key === 'habits.status.label') return 'Status';
      if (key === 'habits.status.progress') return 'Toward weekly target';
      if (key === 'habits.trend.label') return 'Tendency';
      if (key === 'habits.trend.unknown') return 'No comparison period yet';
      if (key === 'habits.period') return 'Period';
      if (key === 'habits.adherence_meter_text') return '100%; 3 of 3 target days';
      if (key === 'habits.type.build') return 'Build habit';
      return key;
    }),
  };
});

vi.mock('$lib/components/trends/TagHeatmap.svelte', () => ({
  default: function TagHeatmapMock(anchor: Element | Comment) {
    const el = document.createElement('div');
    el.setAttribute('data-testid', 'habit-detail-heatmap');
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

const tag = {
  id: 'tag-1',
  user_id: 'user-1',
  slug: 'walk',
  name: 'Walk',
  category: 'sport' as const,
  icon: null,
  color: null,
  is_default: false,
  is_hidden: false,
  include_in_analytics: true,
  habit_type: 'build' as const,
  target_frequency: 4,
  created_at: '2026-05-01T00:00:00Z',
  updated_at: '2026-05-01T00:00:00Z',
};

const baseHabit = {
  tag_id: 'tag-1',
  habit_type: 'build' as const,
  target_frequency: 4,
  window: 28 as const,
  start_date: '2026-05-01',
  end_date: '2026-05-28',
  days_tracked: 10,
  days_total: 28,
  target_days: 16,
  adherence_rate: 62.5,
  previous_adherence_rate: null,
  adherence_delta: null,
  trend_direction: 'unknown' as const,
  correlation_score: null,
  correlation_metric: null,
};

describe('HabitDetailBody', () => {
  it('keeps the heatmap visible when adherence stats are insufficient', () => {
    render(HabitDetailBody, {
      props: {
        selected: {
          tag,
          habit: { ...baseHabit, days_tracked: 2, target_days: 16 },
        },
        detailHeatmap: null,
      },
    });

    expect(screen.getByTestId('habit-insufficient-data')).toBeTruthy();
    expect(screen.getByTestId('habit-detail-heatmap')).toBeTruthy();
    expect(screen.queryByRole('meter')).toBeNull();
  });

  it('shows adherence meter when low-frequency target is met', () => {
    render(HabitDetailBody, {
      props: {
        selected: {
          tag,
          habit: {
            ...baseHabit,
            window: 7,
            days_total: 7,
            target_days: 3,
            days_tracked: 3,
            adherence_rate: 100,
          },
        },
        detailHeatmap: null,
      },
    });

    expect(screen.queryByTestId('habit-insufficient-data')).toBeNull();
    expect(screen.getByRole('meter')).toBeTruthy();
    expect(screen.getByRole('meter').getAttribute('aria-valuetext')).toBe(
      '100%; 3 of 3 target days'
    );
    expect(screen.getByText('Toward weekly target')).toBeTruthy();
  });
});
