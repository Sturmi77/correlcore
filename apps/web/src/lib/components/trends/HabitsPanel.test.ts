import { render, screen, fireEvent } from '@testing-library/svelte';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import HabitsPanel from './HabitsPanel.svelte';

beforeEach(() => {
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: vi.fn().mockImplementation((query: string) => ({
      matches: false,
      media: query,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    })),
  });
});

vi.mock('svelte-i18n', async () => {
  const { readable } = await import('svelte/store');
  return {
    _: readable((key: string, options?: { values?: Record<string, unknown> }) => {
      const values = options?.values ?? {};
      if (key === 'habits.window_last') return `last ${values.n} days`;
      if (key === 'habits.correlation_brief') return `r=${values.score} ${values.metric}`;
      if (key === 'habits.correlation_pending') return 'No correlation data yet';
      if (key === 'habits.correlation_predictor') {
        return `${values.name} predictor r=${values.score}`;
      }
      if (key === 'habits.insufficient_data') return 'Not enough data yet';
      return options?.values?.n ? `${key}:${options.values.n}` : key;
    }),
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
    correlation_metric: 'mood',
  },
];

describe('HabitsPanel', () => {
  it('renders habit rows with adherence and correlation summary', () => {
    render(HabitsPanel, { props: { habits, tags, window: 28 } });

    expect(screen.getAllByText('Walk')).toHaveLength(2);
    expect(screen.getByText(/63% · last 28 days/)).toBeTruthy();
    expect(screen.getByText('r=0.72 mood')).toBeTruthy();
    expect(screen.getByText('Walk predictor r=0.72')).toBeTruthy();
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

  it('shows insufficient-data state for sparse habits', () => {
    render(HabitsPanel, {
      props: {
        habits: [{ ...habits[0], days_tracked: 2 }],
        tags,
        window: 28,
      },
    });

    expect(screen.getByTestId('habit-insufficient-data')).toBeTruthy();
    expect(screen.getByText('Not enough data yet')).toBeTruthy();
  });
});
