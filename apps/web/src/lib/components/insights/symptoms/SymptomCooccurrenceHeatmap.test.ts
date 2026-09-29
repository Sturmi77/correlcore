import { render, screen, fireEvent } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import SymptomCooccurrenceHeatmap from './SymptomCooccurrenceHeatmap.svelte';

vi.mock('svelte-i18n', async () => {
  const { readable } = await import('svelte/store');
  return {
    _: readable((key: string, options?: { values?: Record<string, unknown> }) => {
      if (options?.values) return `${key}:${JSON.stringify(options.values)}`;
      return key;
    }),
  };
});

const data = {
  range: '90d' as const,
  start_date: '2026-02-09',
  end_date: '2026-05-09',
  min_count: 3,
  cells: [
    {
      symptom: {
        symptom_id: 'sym-1',
        slug: 'headache',
        name: 'Headache',
        icon: 'activity',
      },
      tag: {
        tag_id: 'tag-1',
        slug: 'sport',
        name: 'Sport',
        category: 'sport',
        color: null,
      },
      co_count: 4,
      symptom_count: 6,
      tag_count: 8,
      total_count: 30,
      phi: 0.2,
      jaccard: 0.5,
      lift: 2.1,
      p_value: 0.01,
      p_value_corrected: 0.04,
      confounder: null,
    },
  ],
};

describe('SymptomCooccurrenceHeatmap', () => {
  });

  it('renders insufficient data as an uncomputed analysis state', () => {
    render(SymptomCooccurrenceHeatmap, {
      props: {
        data: { ...data, cells: [], analysis_status: 'insufficient_data' },
        phase: 'provisional',
      },
    });

    expect(
      screen.getByText('insights.symptoms.cooccurrence_status_insufficient_data')
    ).toBeTruthy();
