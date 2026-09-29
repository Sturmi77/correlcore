import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/svelte';
import type { InsightResponse } from '$lib/api/insights';
import { parseAdjustedEffects } from '$lib/utils/adjustedEffects';
import AdjustedEffects from './AdjustedEffects.svelte';

vi.mock('svelte-i18n', async () => {
  const { readable } = await import('svelte/store');
  return { _: readable((key: string) => key) };
});

const base: InsightResponse = {
  id: 'i',
  user_id: 'u',
  insight_type: 'pointbiserial',
  tier: 'robust',
  metric: 'mood_score',
  subject_type: 'tag',
  subject_id: 't',
  subject_label: 'Sport',
  effect_size: 0.4,
  confidence: 0.8,
  sample_n: 30,
  statement: null,
  flags: {},
  payload: {
    tagged_mood_avg: 4,
    untagged_mood_avg: 3,
    weekday_held_coefficient: 0,
    calendar_held_coefficient: null,
  },
  generated_for_date: '2026-09-22',
  generated_at: '2026-09-22T00:00:00Z',
  created_at: '2026-09-22T00:00:00Z',
  updated_at: '2026-09-22T00:00:00Z',
};

describe('adjusted effect disclosure', () => {
  it('distinguishes measured zero from unavailable and keeps r separate from point differences', async () => {
    render(AdjustedEffects, { insight: base });
    const details = screen.getByTestId('adjusted-effects') as HTMLDetailsElement;
    expect(details.open).toBe(false);
    await fireEvent.click(screen.getByTestId('adjusted-effects-toggle'));
    expect(details.open).toBe(true);
    expect(screen.getByTestId('adjusted-raw-r').textContent).toBe('0.400');
    expect(screen.getByTestId('adjusted-raw-difference').textContent).toBe('1.000');
    expect(screen.getByTestId('adjusted-weekday').textContent).toBe('0.000');
    expect(screen.getByTestId('adjusted-calendar').textContent).toContain('adjusted_unavailable');
  });

  it('labels absent historical coefficients as not calculated', () => {
    const view = parseAdjustedEffects({ ...base, payload: {} });
    expect(view?.weekday.state).toBe('not_calculated');
    expect(view?.calendar.state).toBe('not_calculated');
  });

  it('states when this insight family has no adjusted model', () => {
    render(AdjustedEffects, { insight: { ...base, insight_type: 'belastung_pattern' } });
    expect(screen.getByTestId('adjusted-unsupported').textContent).toContain(
      'adjusted_unsupported'
    );
  });
});
