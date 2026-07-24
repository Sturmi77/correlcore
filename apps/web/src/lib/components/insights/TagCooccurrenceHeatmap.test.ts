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

  it('hides range controls when showRangeSelector is false', () => {
    render(TagCooccurrenceHeatmap, {
      props: { data, loading: false, range: '90d', showRangeSelector: false },
    });

    expect(screen.queryByRole('button', { name: 'insights.cooccurrence.range_1y' })).toBeNull();
  });

  it('dispatches range changes from the range control', async () => {
    const handler = vi.fn();
    render(TagCooccurrenceHeatmap, {
      props: { data, loading: false, range: '90d' },
      events: { rangeChange: handler },
    });

    await fireEvent.click(screen.getByRole('button', { name: 'insights.cooccurrence.range_1y' }));

    expect(handler).toHaveBeenCalledOnce();
    expect(handler.mock.calls[0][0].detail).toEqual({ range: '1y' });
  });

  // #489: tag-a Focus, tag-c Coffee, tag-d Read in cluster 1; tag-b Walk in cluster 2.
  const clusterMeta = {
    byTagId: new Map([
      ['tag-a', 1],
      ['tag-c', 1],
      ['tag-d', 1],
      ['tag-b', 2],
    ]),
    labels: [
      { cluster_id: 1, label: 'Morning' },
      { cluster_id: 2, label: 'Movement' },
    ],
  };
  const emptyMeta = { byTagId: new Map<string, number>(), labels: [] };

  it('renders a focus chip per cluster plus an all-groups chip (#489)', () => {
    render(TagCooccurrenceHeatmap, {
      props: {
        data,
        loading: false,
        range: '90d',
        sortMode: 'clustered',
        enableClusterSort: true,
        clusterMeta,
      },
    });
    const focus = screen.getByTestId('tag-cooccurrence-focus');
    expect(focus.textContent).toContain('insights.cooccurrence.focus_all');
    expect(focus.textContent).toContain('Morning');
    expect(focus.textContent).toContain('Movement');
    expect(screen.getAllByTestId('tag-cooccurrence-focus-chip')).toHaveLength(2);
  });

  it('draws cluster boundaries in the grid when clustered (#489)', () => {
    const { container } = render(TagCooccurrenceHeatmap, {
      props: {
        data,
        loading: false,
        range: '90d',
        sortMode: 'clustered',
        enableClusterSort: true,
        clusterMeta,
      },
    });
    expect(container.querySelectorAll('.cooccurrence__boundary-left').length).toBeGreaterThan(0);
  });

  it('shows no chips or boundaries without clusters (#489 fallback)', () => {
    const { container } = render(TagCooccurrenceHeatmap, {
      props: {
        data,
        loading: false,
        range: '90d',
        sortMode: 'clustered',
        enableClusterSort: true,
        clusterMeta: emptyMeta,
      },
    });
    expect(screen.queryByTestId('tag-cooccurrence-focus')).toBeNull();
    expect(container.querySelectorAll('.cooccurrence__boundary-left').length).toBe(0);
  });

  it('dispatches focusClusterChange and toggles off on a second click (#489)', async () => {
    const handler = vi.fn();
    render(TagCooccurrenceHeatmap, {
      props: {
        data,
        loading: false,
        range: '90d',
        sortMode: 'clustered',
        enableClusterSort: true,
        clusterMeta,
      },
      events: { focusClusterChange: handler },
    });
    const chips = screen.getAllByTestId('tag-cooccurrence-focus-chip');
    await fireEvent.click(chips[0]);
    expect(handler.mock.calls[0][0].detail).toEqual({ clusterId: 1 });
    await fireEvent.click(chips[0]);
    expect(handler.mock.calls[1][0].detail).toEqual({ clusterId: null });
  });

  it('collapses and expands axes with density controls', async () => {
    render(TagCooccurrenceHeatmap, {
      props: { data, loading: false, range: '90d' },
    });

    const status = screen.getByTestId('tag-cooccurrence-density-status');
    expect(status.textContent).toContain('"visible":6');
    expect(status.textContent).toContain('"total":6');

    const decrease = screen.getByTestId('tag-cooccurrence-density-decrease');
    await fireEvent.click(decrease);
    expect(screen.getByTestId('tag-cooccurrence-density-status').textContent).toContain(
      '"visible":5'
    );

    // Shrink to minimum (4)
    await fireEvent.click(decrease);
    expect(screen.getByTestId('tag-cooccurrence-density-status').textContent).toContain(
      '"visible":4'
    );
    expect(decrease.hasAttribute('disabled')).toBe(true);

    const increase = screen.getByTestId('tag-cooccurrence-density-increase');
    await fireEvent.click(increase);
    expect(screen.getByTestId('tag-cooccurrence-density-status').textContent).toContain(
      '"visible":5'
    );
  });
});
