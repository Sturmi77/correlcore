import { describe, expect, it } from 'vitest';
import type { InsightResponse } from '$lib/api/insights';
import {
  canShowAdvancedAnalytics,
  canShowMatrixTab,
  canShowSymptomCooccurrence,
  canShowTagCooccurrence,
  hasSymptomCooccurrenceData,
  hasTagCooccurrenceData,
} from './insightAnalyticsGate';

const matrixInsight = (id: string): InsightResponse => ({
  id,
  user_id: 'user',
  insight_type: 'pointbiserial',
  tier: 'developing',
  metric: 'mood',
  subject_type: 'tag',
  subject_id: id,
  subject_label: id,
  effect_size: 0.4,
  confidence: 0.5,
  sample_n: 12,
  statement: 'test',
  flags: {},
  payload: {},
  generated_for_date: '2026-06-01',
  generated_at: '2026-06-01T00:00:00Z',
  created_at: '2026-06-01T00:00:00Z',
  updated_at: '2026-06-01T00:00:00Z',
});

describe('insightAnalyticsGate', () => {
  it('gates advanced analytics after collecting', () => {
    expect(canShowAdvancedAnalytics(null)).toBe(false);
    expect(canShowAdvancedAnalytics('collecting')).toBe(false);
    expect(canShowAdvancedAnalytics('early_patterns')).toBe(true);
  });

  it('requires early_patterns and enough matrix insights', () => {
    const insights = [matrixInsight('a'), matrixInsight('b')];
    expect(canShowMatrixTab('collecting', insights)).toBe(false);
    expect(canShowMatrixTab('early_patterns', [matrixInsight('a')])).toBe(false);
    expect(canShowMatrixTab('early_patterns', insights)).toBe(true);
  });

  it('keeps the matrix visible when rows soften into the weak band (#725)', () => {
    // Two correlations dip below 0.2 (weakened) — the section must not disappear.
    const weakened = [
      { ...matrixInsight('a'), confidence: 0.18 },
      { ...matrixInsight('b'), confidence: 0.15 },
    ];
    expect(canShowMatrixTab('early_patterns', weakened)).toBe(true);
    // Below the weak floor there is genuinely nothing to show.
    const noise = [
      { ...matrixInsight('a'), confidence: 0.05 },
      { ...matrixInsight('b'), confidence: 0.04 },
    ];
    expect(canShowMatrixTab('early_patterns', noise)).toBe(false);
  });

  it('gates co-occurrence surfaces by maturity', () => {
    expect(canShowTagCooccurrence('collecting')).toBe(false);
    expect(canShowTagCooccurrence('early_patterns')).toBe(true);
    expect(canShowSymptomCooccurrence('early_patterns')).toBe(false);
    expect(canShowSymptomCooccurrence('provisional')).toBe(true);
  });

  it('detects co-occurrence payload presence', () => {
    expect(hasTagCooccurrenceData(null)).toBe(false);
    expect(
      hasTagCooccurrenceData({
        range: '90d',
        start_date: '2026-01-01',
        end_date: '2026-03-01',
        min_count: 2,
        pairs: [],
      })
    ).toBe(false);
    expect(
      hasTagCooccurrenceData({
        range: '90d',
        start_date: '2026-01-01',
        end_date: '2026-03-01',
        min_count: 2,
        pairs: [
          {
            tag_a: { tag_id: 'a', slug: 'a', name: 'A', category: 'work', color: null },
            tag_b: { tag_id: 'b', slug: 'b', name: 'B', category: 'work', color: null },
            count: 2,
            pct_of_a: 0.5,
            pct_of_b: 0.5,
          },
        ],
      })
    ).toBe(true);
    expect(
      hasSymptomCooccurrenceData({
        range: '90d',
        start_date: '',
        end_date: '',
        min_count: 2,
        cells: [],
      })
    ).toBe(false);
  });
});
