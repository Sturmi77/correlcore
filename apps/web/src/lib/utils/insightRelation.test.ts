import { describe, expect, it } from 'vitest';
import type { InsightResponse } from '$lib/api/insights';
import { insightRelation, relationPairLabel, insightEndpoints } from './insightRelation';

const base = {
  id: '1',
  user_id: 'u',
  insight_type: 'symptom_cluster',
  tier: 'robust',
  metric: 'mood_score',
  subject_type: 'metric',
  subject_id: null,
  subject_label: 'Mood',
  effect_size: 0.4,
  confidence: 0.8,
  sample_n: 30,
  statement: null,
  flags: {},
  payload: {},
  generated_for_date: '2026-09-22',
  generated_at: '2026-09-22T00:00:00Z',
  created_at: '2026-09-22T00:00:00Z',
  updated_at: '2026-09-22T00:00:00Z',
} satisfies InsightResponse;

describe('insightRelation', () => {
  it.each([
    [2, '→', 'Sport → Mood (+2d)'],
    [-2, '←', 'Sport ← Mood (-2d)'],
    [0, '↔', 'Sport ↔ Mood (0d)'],
  ] as const)('orients signed lag %i', (lag, glyph, label) => {
    const insight = { ...base, payload: { method: 'lag', lag_days: lag } };
    expect(insightRelation(insight).glyph).toBe(glyph);
    expect(relationPairLabel(insight, 'Sport', 'Mood')).toBe(label);
  });

  it('never infers time order from a same-day or incomplete correlation', () => {
    expect(relationPairLabel(base, 'Sport', 'Mood')).toBe('Sport ↔ Mood');
    expect(insightRelation({ ...base, payload: { method: 'lag' } }).glyph).toBe('↔');
    expect(insightRelation({ ...base, payload: { method: 'lag', lag_days: null } }).glyph).toBe(
      '↔'
    );
  });
});

it('uses the lag payload and composite endpoints instead of duplicating the target', () => {
  expect(
    insightEndpoints({
      ...base,
      payload: { method: 'lag', feature: { label: 'Sport' }, target: { label: 'Mood' } },
    })
  ).toEqual({ feature: 'Sport', target: 'Mood' });
  expect(
    insightEndpoints({
      ...base,
      payload: { kind: 'symptom_tag_cooccurrence', symptom_name: 'Fatigue', tag_name: 'Work' },
    })
  ).toEqual({ feature: 'Fatigue', target: 'Work' });
});

describe('insightEndpoints localisation', () => {
  const t = (key: string) =>
    ({
      'trends.metric.mood': 'Stimmung',
      'trends.metric.stress': 'Stress',
      'trends.metric.energy': 'Energie',
    })[key] ?? key;

  it('names both metrics of a same-day pair instead of exposing the pair key', () => {
    const pair = {
      ...base,
      insight_type: 'spearman',
      metric: 'stress_mood',
      subject_label: 'mood_score',
      payload: { left_metric: 'stress', right_metric: 'mood_score' },
    } satisfies InsightResponse;
    expect(insightEndpoints(pair, t)).toEqual({ feature: 'Stress', target: 'Stimmung' });
    expect(insightEndpoints(pair)).toEqual({ feature: 'stress', target: 'mood_score' });
  });

  it('localises the metric target but keeps symptom names as entered', () => {
    const symptom = {
      ...base,
      insight_type: 'symptom_mood_association',
      metric: 'stress',
      subject_type: 'symptom',
      subject_label: 'Kopfschmerzen',
    } satisfies InsightResponse;
    expect(insightEndpoints(symptom, t)).toEqual({ feature: 'Kopfschmerzen', target: 'Stress' });
  });

  it('never rewrites a user tag that happens to be called like a metric', () => {
    const tag = { ...base, metric: 'mood_score', subject_type: 'tag', subject_label: 'stress' };
    expect(insightEndpoints(tag, t).feature).toBe('stress');
  });

  it('localises metric-kind lag endpoints only', () => {
    const lag = {
      ...base,
      payload: {
        method: 'lag',
        feature: { kind: 'metric', key: 'energy' },
        target: { kind: 'metric', key: 'stress' },
      },
    } satisfies InsightResponse;
    expect(insightEndpoints(lag, t)).toEqual({ feature: 'Energie', target: 'Stress' });
  });
});
