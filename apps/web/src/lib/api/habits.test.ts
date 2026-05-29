import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('./client', () => ({
  api: {
    get: vi.fn(),
  },
}));

import { api } from './client';
import { fetchHabitStats, listHabits } from './habits';

beforeEach(() => {
  vi.clearAllMocks();
});

describe('habits API client', () => {
  it('lists habits with a window query', async () => {
    vi.mocked(api.get).mockResolvedValueOnce({ habits: [] });
    await listHabits(14);
    expect(api.get).toHaveBeenCalledWith('/habits?window=14');
  });

  it('fetches stats for one habit tag', async () => {
    vi.mocked(api.get).mockResolvedValueOnce({});
    await fetchHabitStats('tag-1', 90);
    expect(api.get).toHaveBeenCalledWith('/habits/tag-1/stats?window=90');
  });
});
