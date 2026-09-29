import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import type { InsightResponse } from '$lib/api/insights';
import BelastungOverlay from './BelastungOverlay.svelte';

vi.mock('svelte-i18n', async () => {
  const { readable } = await import('svelte/store');
  return {
    _: readable(
      (key: string, options?: { values?: Record<string, unknown> }) =>
        `${key}:${JSON.stringify(options?.values ?? {})}`
    ),
  };
});

const base: InsightResponse = {
  id: 'b1',
  user_id: 'u1',
  insight_type: 'belastung_pattern',
  tier: 'robust',
  metric: 'belastung_composite',
  subject_type: 'composite',
  subject_id: null,
  subject_label: 'Load',
  effect_size: 0.3,
  confidence: 0.5,
  sample_n: 14,
  statement: 'Higher stress and fatigue occurred more often together',
  flags: {},
  payload: {
    recent_n: 14,
    prior_n: 14,
    fatigue_days_recent: 4,
    fatigue_days_prior: 2,
    recovery_days_recent: 3,
    recovery_days_prior: 5,
  },
  generated_for_date: '2026-09-22',
  generated_at: '2026-09-22T00:00:00Z',
  created_at: '2026-09-22T00:00:00Z',
  updated_at: '2026-09-22T00:00:00Z',
};

function evidence(stress_up: boolean, energy_down: boolean, fatigue_up: boolean) {
  return {
    family: 'belastung' as const,
    version: 1 as const,
    recent_n: 14,
    prior_n: 14,
    stress_up,
    energy_down,
    fatigue_up,
  };
}

describe('BelastungOverlay evidence wording', () => {
  it.each([
    [true, false, false, 'change_stress'],
    [false, true, false, 'change_energy'],
    [false, false, true, 'change_fatigue'],
  ] as const)('names only the measured marginal change', (stress, energy, fatigue, expected) => {
    render(BelastungOverlay, { insight: { ...base, evidence: evidence(stress, energy, fatigue) } });
    const text = screen.getByTestId('belastung-statement').textContent ?? '';
    expect(text).toContain(expected);
    expect(text).not.toContain('together');
    expect(text).not.toContain(base.statement ?? '');
  });

  it('shows a neutral state for incomplete historical payloads', () => {
    render(BelastungOverlay, { insight: { ...base, evidence: null, payload: {} } });
    expect(screen.getByTestId('belastung-statement').textContent).toContain('insufficient');
    expect(screen.queryByTestId('belastung-frequencies')).toBeNull();
  });
});
