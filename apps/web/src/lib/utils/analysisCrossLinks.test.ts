import { describe, expect, it } from 'vitest';
import type { InsightResponse } from '$lib/api/insights';
import { topInsightLabel } from './analysisCrossLinks';

describe('analysisCrossLinks', () => {
  it('prefers subject_label for display', () => {
    const insight = { subject_label: 'Energy', metric: 'mood' } as InsightResponse;
    expect(topInsightLabel(insight)).toBe('Energy');
  });

  it('falls back to metric when subject_label is empty', () => {
    const insight = { subject_label: '  ', metric: 'sleep' } as InsightResponse;
    expect(topInsightLabel(insight)).toBe('sleep');
  });
});
