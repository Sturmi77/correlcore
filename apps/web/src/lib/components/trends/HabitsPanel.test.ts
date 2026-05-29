import { render, screen, fireEvent } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import HabitsPanel from './HabitsPanel.svelte';

vi.mock('svelte-i18n', async () => {
  const { readable } = await import('svelte/store');
  return {
    _: readable((key: string, options?: { values?: Record<string, unknown> }) =>
      options?.values?.n ? `${key}:${options.values.n}` : key
    ),
  };
});

const tags = [
  {
    id: 'tag-1',
    user_id: 'user-1',
    slug: 'walk',
    name: 'Walk',
    category: 'sport' as const,
    icon: null,
    color: null,
    is_default: false,
    is_hidden: false,
    habit_type: 'build' as const,
    target_frequency: 4,
    created_at: '2026-05-01T00:00:00Z',
    updated_at: '2026-05-01T00:00:00Z',
  },
];

const habits = [
  {
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
    correlation_score: 0.72,
  },
];

describe('HabitsPanel', () => {
  it('renders habit rows and detail metrics', () => {
    render(HabitsPanel, { props: { habits, tags, window: 28 } });

    expect(screen.getAllByText('Walk')).toHaveLength(2);
    expect(screen.getAllByText('63%')[0]).toBeTruthy();
    expect(screen.getByText('0.72')).toBeTruthy();
  });

  it('dispatches window changes', async () => {
    const spy = vi.fn();
    render(HabitsPanel, { props: { habits, tags, window: 28 }, events: { windowChange: spy } });

    await fireEvent.click(screen.getByTestId('habits-window-14'));

    expect(spy).toHaveBeenCalled();
  });

  it('shows neutral empty state', () => {
    render(HabitsPanel, { props: { habits: [], tags: [], window: 28 } });

    expect(screen.getByText('habits.empty')).toBeTruthy();
  });
});
