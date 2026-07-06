import { render, screen } from '@testing-library/svelte';
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
      if (key === 'habits.goal.build') return `${values.tracked} of ${values.target} target days`;
      if (key === 'habits.goal.reduce') return `${values.tracked} of max ${values.target} days`;
      if (key === 'habits.trend.delta') return `${values.delta} pp vs previous period`;
      if (key === 'habits.insufficient_data') return 'Not enough data yet';
      if (key === 'habits.status.progress') return 'Toward weekly target';
      if (key === 'habits.status.within_target') return 'Within target range';
      if (key === 'habits.status.above_target') return 'Above target range';
      if (key === 'trends.metric.mood') return 'mood';
      if (key === 'settings.tags.habit_build') return 'Build';
      if (key === 'settings.tags.habit_reduce') return 'Reduce';
      return options?.values?.n ? `${key}:${options.values.n}` : key;
    }),
  };
});

vi.mock('$lib/api/tags', () => ({
  updateTag: vi.fn().mockResolvedValue({}),
}));

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
    previous_adherence_rate: 50,
    adherence_delta: 12.5,
    trend_direction: 'up' as const,
    correlation_score: 0.72,
    correlation_metric: 'mood',
  },
];

describe('HabitsPanel', () => {
  it('renders habit rows with adherence and correlation summary', () => {
    render(HabitsPanel, { props: { habits, tags, window: 28 } });

    expect(screen.getAllByText('Walk')).toHaveLength(2);
    expect(screen.queryByText(/63%.*last 28 days/)).toBeNull();
    expect(screen.getAllByText('10 of 16 target days')).toHaveLength(2);
    expect(screen.getAllByText('+13 pp vs previous period')).toHaveLength(2);
    expect(screen.getByText('r=0.72 mood')).toBeTruthy();
    expect(screen.getByText('Walk predictor r=0.72')).toBeTruthy();
  });

  it('shows the active global range window label', () => {
    render(HabitsPanel, { props: { habits, tags, window: 28 } });
    expect(screen.getByTestId('habits-window-label').textContent).toContain('last 28 days');
  });

  it('shows inline habit setup when tags are available', () => {
    render(HabitsPanel, {
      props: {
        habits: [],
        tags: [],
        availableTags: [
          {
            id: 'tag-2',
            user_id: 'user-1',
            slug: 'read',
            name: 'Read',
            category: 'leisure',
            icon: null,
            color: null,
            is_default: false,
            is_hidden: false,
            habit_type: 'none',
            target_frequency: null,
            created_at: '2026-05-01T00:00:00Z',
            updated_at: '2026-05-01T00:00:00Z',
          },
        ],
        window: 28,
      },
    });

    expect(screen.getByTestId('habits-empty-setup')).toBeTruthy();
    expect(screen.getByTestId('habits-setup-tag')).toBeTruthy();
    expect(screen.getByText('habits.empty_setup_body')).toBeTruthy();
  });

  it('shows insufficient-data state for sparse high-target habits', () => {
    render(HabitsPanel, {
      props: {
        habits: [{ ...habits[0], days_tracked: 2, target_days: 16 }],
        tags,
        window: 28,
      },
    });

    expect(screen.getByTestId('habit-insufficient-data')).toBeTruthy();
    expect(screen.getByText('Not enough data yet')).toBeTruthy();
  });

  it('shows adherence stats for met low-frequency habits before seven occurrences', () => {
    render(HabitsPanel, {
      props: {
        habits: [
          {
            ...habits[0],
            window: 7,
            days_total: 7,
            target_days: 3,
            days_tracked: 3,
            adherence_rate: 100,
          },
        ],
        tags,
        window: 7,
      },
    });

    expect(screen.queryByTestId('habit-insufficient-data')).toBeNull();
    expect(screen.getByRole('meter')).toBeTruthy();
  });

  it('normalizes mood_score correlation labels', () => {
    render(HabitsPanel, {
      props: {
        habits: [{ ...habits[0], correlation_metric: 'mood_score' }],
        tags,
        window: 28,
      },
    });

    expect(screen.getByText('r=0.72 mood')).toBeTruthy();
  });
});
