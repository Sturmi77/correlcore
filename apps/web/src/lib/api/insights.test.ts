import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('./client', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    delete: vi.fn(),
  },
}));

import { api } from './client';
import {
  fetchTagClusters,
  fetchTagCooccurrence,
  listLatestInsights,
  regenerateInsights,
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

  it('lists insight history', async () => {
    const { listInsights } = await import('./insights');
    vi.mocked(api.get).mockResolvedValueOnce({ insight_maturity: insightMaturity, insights: [] });

    await listInsights({ limit: 25 });

    expect(api.get).toHaveBeenCalledWith('/insights?limit=25');
  });

  it('creates and lists insight dismissals', async () => {
    const { createInsightDismissal, listInsightDismissals, deleteInsightDismissal } =
      await import('./insights');
    vi.mocked(api.post).mockResolvedValueOnce({
      id: 'd1',
      subject_key: 'sk',
      insight_id: 'i1',
      dismissed_at: '2026-05-14T00:00:00Z',
      created_at: '2026-05-14T00:00:00Z',
      insight: null,
    });
    await createInsightDismissal('i1');
    expect(api.post).toHaveBeenCalledWith('/insights/dismissals', { insight_id: 'i1' });

    vi.mocked(api.get).mockResolvedValueOnce({ dismissals: [] });
    await listInsightDismissals();
    expect(api.get).toHaveBeenCalledWith('/insights/dismissals');

    vi.mocked(api.delete).mockResolvedValueOnce(undefined);
    await deleteInsightDismissal('d1');
    expect(api.delete).toHaveBeenCalledWith('/insights/dismissals/d1');
  });

  it('lists insight history', async () => {
    const { listInsightHistory } = await import('./insights');
    vi.mocked(api.get).mockResolvedValueOnce({ insights: [], total: 0, limit: 20, offset: 0 });

    await listInsightHistory({ status: 'all', limit: 20 });

    expect(api.get).toHaveBeenCalledWith('/insights/history?status=all&limit=20');
  });

  it('fetches tag clusters', async () => {
    vi.mocked(api.get).mockResolvedValueOnce({
      status: 'insufficient_data',
      entry_count: 12,
      active_tag_count: 3,
      window_days: 90,
      k: null,
      reason: 'entry_count_below_30',
      clusters: [],
    });

    await fetchTagClusters();

    expect(api.get).toHaveBeenCalledWith('/insights/tag-clusters');
  });

  it('regenerates insights on demand', async () => {
    vi.mocked(api.post).mockResolvedValueOnce({
      status: 'ok',
      generated_for_date: '2026-07-13',
      insight_count: 8,
      tag_clusters_status: 'ok',
      trigger_source: 'user_regenerate',
    });

    const result = await regenerateInsights();

    expect(api.post).toHaveBeenCalledWith('/insights/regenerate');
    expect(result.insight_count).toBe(8);
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
