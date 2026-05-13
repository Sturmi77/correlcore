import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('./client', () => ({
  api: {
    get: vi.fn(),
    patch: vi.fn(),
  },
}));

import { api } from './client';
import { fetchUserPreferences, updateUserPreferences } from './preferences';

beforeEach(() => {
  vi.clearAllMocks();
});

describe('preferences API client', () => {
  it('fetches user preferences', async () => {
    vi.mocked(api.get).mockResolvedValueOnce({ dismissed_insight_keys: [] });
    await fetchUserPreferences();
    expect(api.get).toHaveBeenCalledWith('/user/preferences');
  });

  it('updates user preferences', async () => {
    vi.mocked(api.patch).mockResolvedValueOnce({ dismissed_insight_keys: ['first_week_pattern'] });
    await updateUserPreferences({ dismissed_insight_keys: ['first_week_pattern'] });
    expect(api.patch).toHaveBeenCalledWith('/user/preferences', {
      dismissed_insight_keys: ['first_week_pattern'],
    });
  });
});
