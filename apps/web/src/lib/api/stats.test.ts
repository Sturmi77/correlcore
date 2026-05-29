import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('./client', () => ({
  api: {
    get: vi.fn(),
  },
}));

import { api } from './client';
import { fetchEntryStreak, fetchSymptomHeatmap, fetchTagHeatmap, fetchTimeseries } from './stats';

beforeEach(() => {
  vi.clearAllMocks();
});

describe('stats API client', () => {
  it('fetches time-series by range', async () => {
    vi.mocked(api.get).mockResolvedValueOnce({ range: 'month', points: [] });
    await fetchTimeseries('month');
    expect(api.get).toHaveBeenCalledWith('/entries/stats/timeseries?range=month');
  });

  it('serializes heatmap filters', async () => {
    vi.mocked(api.get).mockResolvedValueOnce({
      start_date: '2026-01-01',
      end_date: '2026-01-31',
      tags: [],
    });
    await fetchTagHeatmap({ start_date: '2026-01-01', end_date: '2026-01-31', category: 'work' });
    const path = vi.mocked(api.get).mock.calls[0][0] as string;
    expect(path).toContain('/entries/stats/tags?');
    expect(path).toContain('start_date=2026-01-01');
    expect(path).toContain('end_date=2026-01-31');
    expect(path).toContain('category=work');
  });

  it('serializes symptom heatmap filters', async () => {
    vi.mocked(api.get).mockResolvedValueOnce({
      start_date: '2026-01-01',
      end_date: '2026-01-31',
      symptoms: [],
    });
    await fetchSymptomHeatmap({ start_date: '2026-01-01', end_date: '2026-01-31' });
    const path = vi.mocked(api.get).mock.calls[0][0] as string;
    expect(path).toContain('/entries/stats/symptoms?');
    expect(path).toContain('start_date=2026-01-01');
    expect(path).toContain('end_date=2026-01-31');
  });

  it('fetches streak with optional as_of', async () => {
    vi.mocked(api.get).mockResolvedValueOnce({ current_streak: 1 });
    await fetchEntryStreak('2026-05-09');
    expect(api.get).toHaveBeenCalledWith('/entries/stats/streak?as_of=2026-05-09');
  });
});
