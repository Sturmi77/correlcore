import { describe, expect, it } from 'vitest';
import type { InsightResponse } from '$lib/api/insights';
import { formatSymptomTagStatement } from './symptomTagStatement';

const base: InsightResponse = {
  id: 'i',
  user_id: 'u',
  insight_type: 'symptom_tag_cooccurrence',
  tier: 'robust',
  metric: 'symptom_tag_cooccurrence',
  subject_type: 'symptom_tag',
  subject_id: null,
  subject_label: 'Headache + Sport',
  effect_size: 2.1,
  confidence: 0.8,
  sample_n: 30,
  statement: 'Historical lift claim',
  flags: {},
  payload: {
    symptom_name: 'Headache',
    tag_name: 'Sport',
    co_count: 4,
    symptom_count: 6,
    tag_count: 8,
    lift: 2.1,
    p_value_corrected: 0.04,
  },
  generated_for_date: '2026-09-22',
  generated_at: '2026-09-22T00:00:00Z',
  created_at: '2026-09-22T00:00:00Z',
  updated_at: '2026-09-22T00:00:00Z',
};

const t = (key: string, options?: { values?: Record<string, string | number> }) =>
  `${key}:${JSON.stringify(options?.values ?? {})}`;

describe('historical symptom-tag wording', () => {
  it('uses measured counts and omits lift or FDR from the sentence', () => {
    const text = formatSymptomTagStatement(base, t) ?? '';
    expect(text).toContain('"together":4');
    expect(text).toContain('"symptomDays":6');
    expect(text).toContain('"tagDays":8');
    expect(text).not.toContain('lift');
  });

  it('shows insufficient evidence for missing or impossible counts', () => {
    expect(formatSymptomTagStatement({ ...base, payload: {} }, t)).toContain(
      'cooccurrence_insufficient'
    );
    expect(
      formatSymptomTagStatement({ ...base, payload: { ...base.payload, co_count: 9 } }, t)
    ).toContain('cooccurrence_insufficient');
  });
});
