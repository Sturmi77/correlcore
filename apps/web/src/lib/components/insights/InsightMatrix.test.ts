import { render, screen, within } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import InsightMatrix from './InsightMatrix.svelte';

vi.mock('svelte-i18n', async () => {
  const { readable } = await import('svelte/store');

  return {
    _: readable((key: string) => key),
  };
});

const base = {
  id: 'insight-1',
  user_id: 'user-1',
  insight_type: 'pointbiserial' as const,
  tier: 'developing' as const,
  metric: 'mood_score',
  subject_type: 'tag',
  subject_id: null,
  subject_label: 'Sport',
  effect_size: 0.4,
  confidence: 0.7,
  sample_n: 24,
  statement: 'Sport lines up with higher mood.',
  flags: { causal_claim: false },
  payload: {},
  generated_for_date: '2026-05-12',
  generated_at: '2026-05-12T03:00:00Z',
  created_at: '2026-05-12T03:00:00Z',
  updated_at: '2026-05-12T03:00:00Z',
};

describe('InsightMatrix', () => {
  it('sorts tag correlations by absolute effect and filters low confidence rows', () => {
    render(InsightMatrix, {
      props: {
        insights: [
          { ...base, id: 'low', subject_label: 'Low confidence', confidence: 0.1 },
          { ...base, id: 'small', subject_label: 'Small', effect_size: 0.2 },
          { ...base, id: 'strong', subject_label: 'Strong', effect_size: -0.7 },
        ],
      },
    });

    const table = screen.getByTestId('insight-matrix');
    const text = within(table)
      .getAllByRole('row')
      .map((row) => row.textContent ?? '');
    expect(text.join(' ')).not.toContain('Low confidence');
    expect(text[1]).toContain('Strong');
    expect(text[2]).toContain('Small');
  });

  it('deduplicates default and override tag rows by slug', () => {
    render(InsightMatrix, {
      props: {
        insights: [
          {
            ...base,
            id: 'default-alcohol',
            subject_id: 'default-id',
            subject_label: 'Alcohol',
            effect_size: 0.3,
            payload: { tag_slug: 'alcohol' },
          },
          {
            ...base,
            id: 'override-alcohol',
            subject_id: 'override-id',
            subject_label: 'Alkohol',
            effect_size: 0.6,
            payload: { tag_slug: 'alcohol' },
          },
        ],
      },
    });

    const rows = within(screen.getByTestId('insight-matrix')).getAllByRole('row');
    expect(rows).toHaveLength(2);
    expect(rows[1].textContent).toContain('Alkohol');
    expect(rows[1].textContent).not.toContain('Alcohol');
  });
});
