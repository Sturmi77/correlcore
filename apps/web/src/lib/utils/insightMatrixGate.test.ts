import { describe, expect, it } from 'vitest';
import type { InsightResponse } from '$lib/api/insights';
import {
  countMatrixInsights,
  isMatrixInsight,
  MATRIX_TAB_MIN_INSIGHTS,
} from './insightMatrixGate';

function insight(partial: Partial<InsightResponse> & Pick<InsightResponse, 'id'>): InsightResponse {
  return {
    user_id: 'user-1',
    insight_type: 'pointbiserial',
    tier: 'developing',
    metric: 'mood',
    subject_type: 'tag',
    subject_id: 'walk',
    subject_label: 'Walk',
    effect_size: 0.4,
    confidence: 0.6,
    sample_n: 10,
    statement: 'Sample',
    flags: {},
    payload: {},
    generated_for_date: '2026-06-01',
    generated_at: '2026-06-01T00:00:00Z',
    created_at: '2026-06-01T00:00:00Z',
    updated_at: '2026-06-01T00:00:00Z',
    ...partial,
  };
}

describe('insightMatrixGate', () => {
  it('counts matrix-ready insights', () => {
    const insights = [
      insight({ id: 'a' }),
      insight({ id: 'b', insight_type: 'spearman' }),
      insight({ id: 'c', confidence: 0.1 }),
    ];
    expect(isMatrixInsight(insights[0])).toBe(true);
    expect(isMatrixInsight(insights[1])).toBe(false);
    expect(isMatrixInsight(insights[2])).toBe(false);
    expect(countMatrixInsights(insights)).toBe(1);
    expect(MATRIX_TAB_MIN_INSIGHTS).toBe(2);
  });
});
