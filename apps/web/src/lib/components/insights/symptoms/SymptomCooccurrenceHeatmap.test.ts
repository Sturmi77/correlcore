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
  it('renders lift values in provisional phase', () => {
    render(SymptomCooccurrenceHeatmap, {
      props: { data, phase: 'provisional' },
    });

    expect(screen.getByText('2.1*')).toBeTruthy();
    expect(screen.getByText('insights.symptoms.cooccurrence_lift_legend')).toBeTruthy();
  });

  it('renders raw counts in early_patterns phase', () => {
    render(SymptomCooccurrenceHeatmap, {
      props: { data, phase: 'early_patterns' },
    });

    expect(screen.getByText('4')).toBeTruthy();
    expect(screen.getByText('insights.symptoms.cooccurrence_count_legend')).toBeTruthy();
  });

  it('dispatches selectCell when a populated cell is clicked', async () => {
    const handler = vi.fn();
    render(SymptomCooccurrenceHeatmap, {
      props: { data, phase: 'provisional' },
      events: { selectCell: handler },
    });

    await fireEvent.click(screen.getByTestId('symptom-cooccurrence-cell'));

    expect(handler).toHaveBeenCalledOnce();
    expect(handler.mock.calls[0]?.[0].detail.cell.symptom.name).toBe('Headache');
  });

  it('applies confounded styling and clustered sort mode', () => {
    const clusteredData = {
      ...data,
      cells: [
        {
          ...data.cells[0],
          confounder: 'weekday' as const,
        },
        {
          symptom: {
            symptom_id: 'sym-2',
            slug: 'nausea',
            name: 'Nausea',
            icon: null,
          },
          tag: {
            tag_id: 'tag-2',
            slug: 'coffee',
            name: 'Coffee',
            category: 'consumption',
            color: null,
          },
          co_count: 3,
          symptom_count: 5,
          tag_count: 6,
          total_count: 30,
          phi: 0.1,
          jaccard: 0.2,
          lift: 1.2,
          p_value: 0.2,
          p_value_corrected: 0.3,
          confounder: null,
        },
      ],
    };

    const { container } = render(SymptomCooccurrenceHeatmap, {
      props: { data: clusteredData, phase: 'robust', sortMode: 'clustered' },
    });

    expect(container.querySelector('.symptom-cooccurrence__cell--confounded')).toBeTruthy();
    expect(screen.getByText(/cooccurrence_confounder_note/)).toBeTruthy();
  });

  it('marks work-context and calendar-context confounders as confounded', async () => {
    const contextData = {
      ...data,
      cells: [
        {
          ...data.cells[0],
          confounder: 'work_context' as const,
        },
      ],
    };

    const { container, rerender } = render(SymptomCooccurrenceHeatmap, {
      props: { data: contextData, phase: 'robust' },
    });

    expect(container.querySelector('.symptom-cooccurrence__cell--confounded')).toBeTruthy();
    expect(screen.getByLabelText(/insights.work_context_confounded_note/)).toBeTruthy();

    await rerender({
      data: {
        ...data,
        cells: [{ ...data.cells[0], confounder: 'calendar_context' as const }],
      },
      phase: 'robust',
    });

    expect(screen.getByLabelText(/insights.calendar_context_confounded_note/)).toBeTruthy();
  });
});
