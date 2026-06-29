import { tick } from 'svelte';
import { render, screen } from '@testing-library/svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import TagHeatmap from './TagHeatmap.svelte';

vi.mock('svelte-i18n', async () => {
  const { readable } = await import('svelte/store');

  return {
    _: readable((key: string) => key),
  };
});

const heatmap = {
  start_date: '2026-05-01',
  end_date: '2026-05-03',
  tags: [
    {
      tag_id: 'tag-1',
      slug: 'focus',
      name: 'Focus',
      category: 'work' as const,
      color: null,
      days: [
        { date: '2026-05-01', count: 1 },
        { date: '2026-05-03', count: 3 },
      ],
    },
  ],
};

describe('TagHeatmap', () => {
  beforeEach(() => {
    Object.defineProperty(HTMLElement.prototype, 'scrollWidth', {
      configurable: true,
      get: () => 1200,
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('scrolls to the newest/rightmost day and renders the intensity legend', async () => {
    render(TagHeatmap, { props: { heatmap, loading: false } });
    await tick();
    await tick();

    const scroller = screen.getByLabelText('trends.heatmap.aria') as HTMLDivElement;
    expect(scroller.scrollLeft).toBe(1200);
    expect(screen.getByText('trends.heatmap.less')).toBeTruthy();
    expect(screen.getByText('trends.heatmap.more')).toBeTruthy();
    expect(screen.getByLabelText('Focus, 2026-05-03: 3')).toBeTruthy();
  });

  it('marks compact heatmaps for dense mobile layouts', () => {
    const { container } = render(TagHeatmap, { props: { heatmap, loading: false, compact: true } });
    expect(container.querySelector('.heatmap--compact')).toBeTruthy();
  });

  it('renders skeleton and empty states', () => {
    const loading = render(TagHeatmap, { props: { heatmap: null, loading: true } });
    expect(loading.getByLabelText('trends.heatmap.loading')).toBeTruthy();
    loading.unmount();

    render(TagHeatmap, {
      props: {
        heatmap: { start_date: '2026-05-01', end_date: '2026-05-03', tags: [] },
        loading: false,
      },
    });
    expect(screen.getByText('trends.heatmap.empty')).toBeTruthy();
    expect(screen.getByText('trends.empty_cta')).toBeTruthy();
  });
});
