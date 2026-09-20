import { describe, expect, it } from 'vitest';
import type { InsightResponse } from '$lib/api/insights';
import {
  isLagInsight,
  isSameDaySleepSpearman,
  lagProfileBars,
  parseLagFrequencyView,
} from './lagInsight';

function lagInsight(overrides: Partial<InsightResponse> = {}): InsightResponse {
  return {
    id: 'lag1',
    user_id: 'u1',
    insight_type: 'symptom_cluster',
    tier: 'robust',
    metric: 'mood_score',
    subject_type: 'metric',
    subject_id: null,
    subject_label: 'mood',
    effect_size: 0.4,
    confidence: 0.5,
    sample_n: 60,
    statement: 'sleep → mood',
    flags: { method: 'lag' },
    payload: {
      method: 'lag',
      lag_days: 1,
      feature: { kind: 'metric', key: 'sleep_minutes', name: 'sleep duration' },
      target: { kind: 'metric', key: 'mood_score', name: 'mood' },
      lag_profile: [
        { lag: 1, r: 0.4 },
        { lag: 2, r: 0.2 },
      ],
      high_feature_n: 30,
      high_feature_good_count: 18,
      low_feature_n: 30,
      low_feature_good_count: 10,
      good_threshold: 4,
    },
    generated_for_date: '2026-05-01',
    generated_at: '2026-05-01T00:00:00Z',
    created_at: '2026-05-01T00:00:00Z',
    updated_at: '2026-05-01T00:00:00Z',
    ...overrides,
  };
}

describe('lagInsight', () => {
  it('detects lag vs same-day sleep Spearman (D4)', () => {
    expect(isLagInsight(lagInsight())).toBe(true);
    expect(
      isSameDaySleepSpearman(
        lagInsight({
          insight_type: 'spearman',
          metric: 'mood_sleep_minutes',
          payload: { left_metric: 'mood_score', right_metric: 'sleep_minutes' },
        })
      )
    ).toBe(true);
  });

  it('builds lag profile bars and frequency view', () => {
    const bars = lagProfileBars(lagInsight());
    expect(bars).toHaveLength(7);
    expect(bars?.[0].active).toBe(true);
    const freq = parseLagFrequencyView(lagInsight());
    expect(freq?.highGood).toBe(18);
    expect(freq?.lowN).toBe(30);
    expect(freq?.lagDays).toBe(1);
  });

  it('marks lags without a measurement as null, never as r = 0', () => {
    // The payload carries lags 1 and 2 only. Lags 3..7 were not measurable, which
    // is a different statement from "measured, and the correlation was zero".
    const bars = lagProfileBars(lagInsight());
    expect(bars?.map((bar) => bar.r)).toEqual([0.4, 0.2, null, null, null, null, null]);
  });

  it('keeps a genuine zero correlation distinct from an absent one', () => {
    const bars = lagProfileBars(
      lagInsight({
        payload: {
          method: 'lag',
          lag_days: 1,
          lag_profile: [
            { lag: 1, r: 0.4 },
            { lag: 2, r: 0 },
          ],
        },
      })
    );
    expect(bars?.[1].r).toBe(0);
    expect(bars?.[2].r).toBeNull();
  });

  it('reports the good-day comparator so "good" is never left undefined', () => {
    expect(parseLagFrequencyView(lagInsight())?.goodDirection).toBe('gte');

    const stress = parseLagFrequencyView(
      lagInsight({
        payload: {
          method: 'lag',
          lag_days: 1,
          lag_profile: [
            { lag: 1, r: -0.4 },
            { lag: 2, r: -0.2 },
          ],
          high_feature_n: 20,
          high_feature_good_count: 8,
          low_feature_n: 20,
          low_feature_good_count: 3,
          good_threshold: 2,
          good_direction: 'lte',
        },
      })
    );
    expect(stress?.goodDirection).toBe('lte');
    expect(stress?.goodThreshold).toBe(2);
  });
});
