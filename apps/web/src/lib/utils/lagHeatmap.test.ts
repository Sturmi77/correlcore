import { describe, expect, it } from 'vitest';
import type { InsightResponse } from '$lib/api/insights';
import { buildLagHeatmapRows, LAG_HEATMAP_MAX_DAYS } from './lagHeatmap';

const baseInsight = (overrides: Partial<InsightResponse>): InsightResponse => ({
  id: 'i1',
  user_id: 'u1',
  insight_type: 'symptom_cluster',
  tier: 'developing',
  metric: 'mood',
  subject_type: 'metric',
  subject_id: null,
  subject_label: 'Mood',
  effect_size: 0.3,
  confidence: 0.5,
  sample_n: 90,
  statement: null,
  flags: {},
  payload: {},
  generated_for_date: '2026-07-01',
  generated_at: '2026-07-01T00:00:00Z',
  created_at: '2026-07-01T00:00:00Z',
  updated_at: '2026-07-01T00:00:00Z',
  ...overrides,
});

const lagInsight = (
  id: string,
  feature: string,
  target: string,
  lagDays: number
): InsightResponse =>
  baseInsight({
    id,
    payload: {
      method: 'lag',
      lag_days: lagDays,
      feature: { kind: 'tag', key: `tag:${feature.toLowerCase()}`, name: feature },
      target: { kind: 'metric', key: target.toLowerCase(), name: target },
      lag_profile: [
        { lag: 1, r: 0.1 },
        { lag: 2, r: 0.42 },
        { lag: 4, r: -0.2 },
      ],
    },
  });

describe('buildLagHeatmapRows', () => {
  it('builds one row per pair with 7 lag cells and the chosen lag marked', () => {
    const rows = buildLagHeatmapRows([
      lagInsight('a', 'Sport', 'Mood', 2),
      lagInsight('b', 'Coffee', 'Energy', 1),
    ]);

    expect(rows).toHaveLength(2);
    expect(rows[0]?.featureName).toBe('Sport');
    expect(rows[0]?.targetName).toBe('Mood');
    expect(rows[0]?.targetKind).toBe('metric');
    expect(rows[0]?.cells).toHaveLength(LAG_HEATMAP_MAX_DAYS);
    // Observed lags carry r; unobserved lags are null.
    expect(rows[0]?.cells[1]).toEqual({ lag: 2, r: 0.42, active: true });
    expect(rows[0]?.cells[2]).toEqual({ lag: 3, r: null, active: false });
    expect(rows[0]?.cells[3]).toEqual({ lag: 4, r: -0.2, active: false });
    // Exactly one active cell per row (the chosen lag).
    expect(rows[0]?.cells.filter((cell) => cell.active)).toHaveLength(1);
  });

  it('collapses multiple findings for the same feature→target pair into one row (#586)', () => {
    // run_lag_analysis emits one insight per surviving lag; they share a profile.
    const rows = buildLagHeatmapRows([
      lagInsight('lag2', 'Sport', 'Mood', 2),
      lagInsight('lag4', 'Sport', 'Mood', 4),
    ]);

    expect(rows).toHaveLength(1);
    expect(rows[0]?.id).toBe('lag2'); // first (strongest) wins
  });

  it('skips non-lag insights and lag insights without a usable profile', () => {
    const rows = buildLagHeatmapRows([
      baseInsight({ id: 'spearman', payload: { method: 'spearman' } }),
      baseInsight({
        id: 'thin',
        payload: { method: 'lag', lag_days: 2, lag_profile: [{ lag: 2, r: 0.4 }] },
      }),
      lagInsight('ok', 'Sport', 'Mood', 2),
    ]);

    expect(rows.map((row) => row.id)).toEqual(['ok']);
  });
});
