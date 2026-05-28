import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { get } from 'svelte/store';

vi.mock('$lib/api/habits', async () => {
  const actual = await vi.importActual<typeof import('$lib/api/habits')>('$lib/api/habits');
  return {
    ...actual,
    listHabits: vi.fn(),
  };
});

import * as habitsApi from '$lib/api/habits';
import { currentHabits, habits, refreshHabits, resetHabitsStore } from './habits';

beforeEach(() => {
  resetHabitsStore();
  vi.clearAllMocks();
});

afterEach(() => {
  resetHabitsStore();
});

describe('habits store', () => {
  it('loads habit stats into ready state', async () => {
    vi.mocked(habitsApi.listHabits).mockResolvedValueOnce({
      habits: [
        {
          tag_id: 'tag-1',
          habit_type: 'build',
          target_frequency: 4,
          window: 28,
          start_date: '2026-05-01',
          end_date: '2026-05-28',
          days_tracked: 10,
          days_total: 28,
          target_days: 16,
          adherence_rate: 62.5,
          correlation_score: null,
        },
      ],
    });

    await refreshHabits(28);

    const state = get(habits);
    expect(state.status).toBe('ready');
    expect(currentHabits()).toHaveLength(1);
  });

  it('transitions to error and rethrows', async () => {
    vi.mocked(habitsApi.listHabits).mockRejectedValueOnce(new Error('boom'));

    await expect(refreshHabits(7)).rejects.toThrow('boom');

    const state = get(habits);
    expect(state.status).toBe('error');
  });
});
