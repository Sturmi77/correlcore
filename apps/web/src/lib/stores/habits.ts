import { get, writable } from 'svelte/store';
import {
  listHabits,
  type HabitListResponse,
  type HabitStatsResponse,
  type HabitWindow,
} from '$lib/api/habits';

export type HabitsState =
  | { status: 'idle' }
  | { status: 'loading'; window: HabitWindow }
  | { status: 'ready'; window: HabitWindow; habits: HabitStatsResponse[] }
  | { status: 'error'; window: HabitWindow; message: string };

const _habits = writable<HabitsState>({ status: 'idle' });

export const habits = { subscribe: _habits.subscribe };

export async function refreshHabits(window: HabitWindow = 28): Promise<HabitListResponse> {
  _habits.set({ status: 'loading', window });
  try {
    const response = await listHabits(window);
    _habits.set({ status: 'ready', window, habits: response.habits });
    return response;
  } catch (err) {
    const message = err instanceof Error ? err.message : 'Failed to load habits';
    _habits.set({ status: 'error', window, message });
    throw err;
  }
}

export function currentHabits(): HabitStatsResponse[] {
  const state = get(_habits);
  return state.status === 'ready' ? state.habits : [];
}

export function resetHabitsStore(): void {
  _habits.set({ status: 'idle' });
}
