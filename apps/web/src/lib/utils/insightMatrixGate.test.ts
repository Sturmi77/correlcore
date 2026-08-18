import { describe, expect, it } from 'vitest';
import type { InsightResponse } from '$lib/api/insights';
import {
  countDisplayableMatrixInsights,
  countMatrixInsights,
  isMatrixInsight,
  isWeakMatrixInsight,
  MATRIX_STRONG_MIN_CONFIDENCE,
  MATRIX_TAB_MIN_INSIGHTS,
  MATRIX_WEAK_MIN_CONFIDENCE,
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

  it('classifies weakened rows in the [weak, strong) band (#725)', () => {
    const strong = insight({ id: 'strong', confidence: MATRIX_STRONG_MIN_CONFIDENCE });
    const weak = insight({ id: 'weak', confidence: 0.15 });
    const weakFloor = insight({ id: 'floor', confidence: MATRIX_WEAK_MIN_CONFIDENCE });
    const noise = insight({ id: 'noise', confidence: 0.05 });

    expect(isMatrixInsight(strong)).toBe(true);
    expect(isWeakMatrixInsight(strong)).toBe(false);

    expect(isWeakMatrixInsight(weak)).toBe(true);
    expect(isMatrixInsight(weak)).toBe(false);
    expect(isWeakMatrixInsight(weakFloor)).toBe(true);

    expect(isWeakMatrixInsight(noise)).toBe(false);
    expect(isMatrixInsight(noise)).toBe(false);
  });

  it('keeps the matrix renderable when strong rows soften into the weak band (#725)', () => {
    // Regression: a later run softens both strong correlations below 0.2.
    // Reliable count drops to 0, but the displayable count stays >= 2 so the
    // section survives (collapsed) instead of vanishing.
    const softened = [
      insight({ id: 'coffee', confidence: 0.18 }),
      insight({ id: 'sleep', confidence: 0.15 }),
    ];
    expect(countMatrixInsights(softened)).toBe(0);
    expect(countDisplayableMatrixInsights(softened)).toBe(2);
  });
});
