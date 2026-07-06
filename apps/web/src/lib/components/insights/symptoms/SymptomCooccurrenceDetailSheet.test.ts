import { render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import SymptomCooccurrenceDetailSheet from './SymptomCooccurrenceDetailSheet.svelte';

vi.mock('svelte-i18n', async () => {
  const { readable } = await import('svelte/store');
  return {
    _: readable((key: string, options?: { values?: Record<string, unknown> }) => {
      if (options?.values) return `${key}:${JSON.stringify(options.values)}`;
      return key;
    }),
  };
});

const cell = {
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
  confounder: 'work_context' as const,
};

describe('SymptomCooccurrenceDetailSheet', () => {
  it('renders specific copy for work-context confounded cells', () => {
    render(SymptomCooccurrenceDetailSheet, {
      props: { open: true, cell },
    });

    expect(screen.getByText('insights.work_context_confounded_note')).toBeTruthy();
  });

  it('renders specific copy for calendar-context confounded cells', () => {
    render(SymptomCooccurrenceDetailSheet, {
      props: {
        open: true,
        cell: {
          ...cell,
          confounder: 'calendar_context' as const,
        },
      },
    });

    expect(screen.getByText('insights.calendar_context_confounded_note')).toBeTruthy();
  });
});
