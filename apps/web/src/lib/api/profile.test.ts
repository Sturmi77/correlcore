import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('./client', () => ({
  api: {
    get: vi.fn(),
    put: vi.fn(),
  },
}));

import { api } from './client';
import { fetchUserProfile, upsertUserProfile } from './profile';

beforeEach(() => {
  vi.clearAllMocks();
});

describe('profile API client', () => {
  it('fetches profile answers', async () => {
    vi.mocked(api.get).mockResolvedValueOnce({ user_id: 'u1', work_context_typical: 'office' });
    await fetchUserProfile();
    expect(api.get).toHaveBeenCalledWith('/user/profile');
  });

  it('upserts profile answers', async () => {
    vi.mocked(api.put).mockResolvedValueOnce({ user_id: 'u1' });
    await upsertUserProfile({ sleep_hours_typical: '7h', insight_curiosity: 'energy_sleep' });
    expect(api.put).toHaveBeenCalledWith('/user/profile', {
      sleep_hours_typical: '7h',
      insight_curiosity: 'energy_sleep',
    });
  });
});
