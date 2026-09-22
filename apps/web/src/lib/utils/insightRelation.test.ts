import { describe, expect, it } from 'vitest';
import type { InsightResponse } from '$lib/api/insights';
import { insightRelation, relationPairLabel } from './insightRelation';

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
