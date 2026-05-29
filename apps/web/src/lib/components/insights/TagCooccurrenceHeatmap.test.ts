import { fireEvent, render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import TagCooccurrenceHeatmap from './TagCooccurrenceHeatmap.svelte';

vi.mock('svelte-i18n', async () => {
  const { readable } = await import('svelte/store');

  return {
    _: readable((key: string, options?: { values?: Record<string, unknown> }) => {
      if (options?.values) {
        return `${key}:${JSON.stringify(options.values)}`;
      }
      return key;
    }),
  };
});

const data = {
  range: '90d' as const,
  start_date: '2026-02-09',
  end_date: '2026-05-09',
  min_count: 2,
  pairs: [
    {
      tag_a: {
        tag_id: 'tag-a',
        slug: 'focus',
        name: 'Focus',
        category: 'work',
        color: null,
      },
      tag_b: {
        tag_id: 'tag-b',
        slug: 'walk',
        name: 'Walk',
        category: 'sport',
        color: null,
      },
      count: 3,
      pct_of_a: 75,
      pct_of_b: 60,
    },
    {
      tag_a: {
        tag_id: 'tag-a',
        slug: 'focus',
        name: 'Focus',
        category: 'work',
        color: null,
      },
      tag_b: {
        tag_id: 'tag-c',
        slug: 'coffee',
        name: 'Coffee',
        category: 'consumption',
        color: null,
      },
      count: 2,
      pct_of_a: 50,
      pct_of_b: 40,
    },
    {
      tag_a: {
        tag_id: 'tag-b',
        slug: 'walk',
        name: 'Walk',
        category: 'sport',
        color: null,
      },
      tag_b: {
        tag_id: 'tag-c',
        slug: 'coffee',
        name: 'Coffee',
        category: 'consumption',
        color: null,
      },
      count: 2,
      pct_of_a: 40,
      pct_of_b: 40,
    },
    {
      tag_a: {
        tag_id: 'tag-d',
        slug: 'read',
        name: 'Read',
        category: 'leisure',
        color: null,
      },
      tag_b: {
        tag_id: 'tag-e',
        slug: 'music',
        name: 'Music',
        category: 'leisure',
        color: null,
      },
      count: 2,
      pct_of_a: 100,
      pct_of_b: 100,
    },
    {
      tag_a: {
        tag_id: 'tag-d',
        slug: 'read',
        name: 'Read',
        category: 'leisure',
        color: null,
      },
      tag_b: {
        tag_id: 'tag-f',
        slug: 'tea',
        name: 'Tea',
        category: 'consumption',
        color: null,
      },
      count: 2,
      pct_of_a: 100,
      pct_of_b: 100,
    },
  ],
};

describe('TagCooccurrenceHeatmap', () => {
  it('renders matrix cells and dispatches pair selection', async () => {
    const handler = vi.fn();
    render(TagCooccurrenceHeatmap, {
      props: { data, loading: false, range: '90d' },
      events: { selectPair: handler },
    });

    expect(screen.getByText('insights.cooccurrence.heading')).toBeTruthy();
    expect(screen.getByRole('grid')).toBeTruthy();

    const cell = screen.getByTitle(
      'insights.cooccurrence.cell_title:{"tagA":"Focus","tagB":"Walk","count":3}'
    );
    await fireEvent.click(cell);

    expect(handler).toHaveBeenCalled();
  });

  it('shows empty state when fewer than five pairs exist', () => {
    render(TagCooccurrenceHeatmap, {
      props: {
        data: { ...data, pairs: data.pairs.slice(0, 2) },
        loading: false,
        range: '90d',
      },
    });

    expect(screen.getByText('insights.cooccurrence.empty')).toBeTruthy();
  });

  it('shows loading skeleton', () => {
    render(TagCooccurrenceHeatmap, {
      props: { data: null, loading: true, range: '90d' },
    });

    expect(screen.getByLabelText('insights.cooccurrence.loading')).toBeTruthy();
  });
});
