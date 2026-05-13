import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('./client', () => ({
  api: {
    get: vi.fn(),
  },
}));

import { api } from './client';
import { fetchDashboardSummary } from './dashboard';

beforeEach(() => {
  vi.clearAllMocks();
});

describe('dashboard API client', () => {
  it('fetches dashboard summary with optional as_of', async () => {
    vi.mocked(api.get).mockResolvedValueOnce({
      entry_count: 15,
      insight_tier: 'developing',
      confidence_score: 0.65,
    });

    await fetchDashboardSummary('2026-05-12');

    expect(api.get).toHaveBeenCalledWith('/dashboard/summary?as_of=2026-05-12');
  });
});
