import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('./client', () => ({
  api: {
    get: vi.fn(),
  },
}));

import { api } from './client';
import {
  fetchTagClusters,
  fetchTagCooccurrence,
  listLatestInsights,
  type InsightMaturity,
} from './insights';

beforeEach(() => {
  vi.clearAllMocks();
});

const insightMaturity: InsightMaturity = {
  phase: 'provisional',
  phase_index: 3,
  current_entries: 18,
  next_phase_at: 30,
  next_phase_label: 'Robust Insights',
  entries_until_next: 12,
  user_message_key: 'maturity.provisional.description',
};

describe('insights API client', () => {
  it('lists latest insights', async () => {
    vi.mocked(api.get).mockResolvedValueOnce({ insight_maturity: insightMaturity, insights: [] });

    await listLatestInsights({ limit: 3 });

    expect(api.get).toHaveBeenCalledWith('/insights/latest?limit=3');
  });

  it('fetches tag clusters', async () => {
    vi.mocked(api.get).mockResolvedValueOnce({
      status: 'insufficient_data',
      entry_count: 12,
      active_tag_count: 3,
      window_days: 90,
      k: null,
      reason: 'entry_count_below_90',
      clusters: [],
    });

    await fetchTagClusters();

    expect(api.get).toHaveBeenCalledWith('/insights/tag-clusters');
  });

  it('fetches tag cooccurrence with query params', async () => {
    vi.mocked(api.get).mockResolvedValueOnce({
      range: '30d',
      start_date: '2026-04-12',
      end_date: '2026-05-12',
      min_count: 2,
      pairs: [],
    });

    await fetchTagCooccurrence({ range: '30d', min_count: 2 });

    expect(api.get).toHaveBeenCalledWith('/insights/tag-cooccurrence?range=30d&min_count=2');
  });
});
