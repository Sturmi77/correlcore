import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('./client', () => ({
  api: {
    get: vi.fn(),
  },
}));

import { api } from './client';
import { fetchLatestInsight, listInsights, listLatestInsights } from './insights';

beforeEach(() => {
  vi.clearAllMocks();
});

const insight = {
  id: 'insight-1',
  user_id: 'user-1',
  insight_type: 'spearman' as const,
  tier: 'preliminary' as const,
  metric: 'mood_score',
  subject_type: 'metric',
  subject_id: null,
  subject_label: 'energy',
  effect_size: 0.41,
  confidence: 0.62,
  sample_n: 18,
  statement: 'Energy and mood currently move together in your entries.',
  flags: { causal_claim: false },
  payload: {},
  generated_for_date: '2026-05-12',
  generated_at: '2026-05-12T03:00:00Z',
  created_at: '2026-05-12T03:00:00Z',
  updated_at: '2026-05-12T03:00:00Z',
};

describe('insights API client', () => {
  it('lists insights with optional limit', async () => {
    vi.mocked(api.get).mockResolvedValueOnce({ insights: [] });

    await listInsights({ limit: 20 });

    expect(api.get).toHaveBeenCalledWith('/insights?limit=20');
  });

  it('lists latest insights', async () => {
    vi.mocked(api.get).mockResolvedValueOnce({ insights: [] });

    await listLatestInsights({ limit: 3 });

    expect(api.get).toHaveBeenCalledWith('/insights/latest?limit=3');
  });

  it('returns the first latest insight for the home preview', async () => {
    vi.mocked(api.get).mockResolvedValueOnce({ insights: [insight] });

    await expect(fetchLatestInsight()).resolves.toEqual(insight);
    expect(api.get).toHaveBeenCalledWith('/insights/latest?limit=1');
  });

  it('returns null when no latest insight exists yet', async () => {
    vi.mocked(api.get).mockResolvedValueOnce({ insights: [] });

    await expect(fetchLatestInsight()).resolves.toBeNull();
  });
});
