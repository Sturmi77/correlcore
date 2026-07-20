import { render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import ComparisonHeatmapHarness from './ComparisonHeatmap.harness.svelte';

vi.mock('svelte-i18n', async () => {
  const { readable } = await import('svelte/store');
  return {
    _: readable((key: string) => key),
    locale: readable('en'),
    isLoading: readable(false),
  };
});

describe('ComparisonHeatmap shared axis', () => {
  it('keeps empty date columns when pruneSparseAxes is on so chart alignment holds', () => {
    render(ComparisonHeatmapHarness, { props: { pruneSparseAxes: true } });

    const cells = screen.getAllByRole('button').filter((el) => el.hasAttribute('data-date'));
    const dates = [...new Set(cells.map((cell) => cell.getAttribute('data-date')))];
    expect(dates).toEqual(['2026-07-01', '2026-07-02', '2026-07-03']);
    // Empty tag row is pruned; active row remains.
    expect(screen.getByText('Run')).toBeTruthy();
    expect(screen.queryByText('Empty')).toBeNull();
  });

  it('aggregates multi-day buckets as summed occurrence counts', () => {
    render(ComparisonHeatmapHarness, {
      props: {
        pruneSparseAxes: false,
        dates: ['2026-07-01', '2026-07-02', '2026-07-03'],
        buckets: [
          {
            id: '2026-07-01_2026-07-03',
            start: '2026-07-01',
            end: '2026-07-03',
            dayCount: 3,
            presentDays: 3,
            partial: false,
            dates: ['2026-07-01', '2026-07-02', '2026-07-03'],
          },
        ],
      },
    });

    const cells = screen.getAllByRole('button').filter((el) => el.hasAttribute('data-date'));
    const runCell = cells.find((cell) => cell.getAttribute('aria-label')?.startsWith('Run,'));
    expect(runCell?.getAttribute('data-date')).toBe('2026-07-01');
    // Run has count 2 on day 1 only → bucket sum 2.
    expect(runCell?.getAttribute('aria-label')).toContain(': 2');
  });
});
