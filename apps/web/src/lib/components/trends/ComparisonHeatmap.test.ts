import { render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import ComparisonHeatmapHarness from './ComparisonHeatmap.harness.svelte';

vi.mock('svelte-i18n', async () => {
  const { readable } = await import('svelte/store');
  return {
    _: readable((key: string, opts?: { values?: Record<string, unknown> }) => {
      if (key === 'trends.compare.zoom.coverage' && opts?.values) {
        return `Logged days ${opts.values.active} of ${opts.values.present}`;
      }
      if (key === 'trends.compare.zoom.cell_tooltip_zoom' && opts?.values) {
        return `${opts.values.label}, ${opts.values.range}: ${opts.values.value} · ${opts.values.coverage} · Tap to zoom in`;
      }
      if (key === 'trends.compare.zoom.cell_tooltip' && opts?.values) {
        return `${opts.values.label}, ${opts.values.range}: ${opts.values.value} · ${opts.values.coverage}`;
      }
      return key;
    }),
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
    expect(runCell?.getAttribute('data-zoomable')).toBe('true');
    // Run has count 2 on day 1 only → bucket sum 2; tooltip includes coverage + zoom affordance.
    expect(runCell?.getAttribute('aria-label')).toContain(': 2');
    expect(runCell?.getAttribute('aria-label')).toContain('Tap to zoom in');
    expect(runCell?.getAttribute('aria-label')).toContain('Logged days');
  });

  it('orders tag rows by server cluster when sortMode is clustered (#592)', () => {
    render(ComparisonHeatmapHarness, {
      props: {
        pruneSparseAxes: false,
        sortMode: 'clustered',
        clusterMeta: {
          byTagId: new Map([
            ['t1', 2],
            ['t2', 1],
          ]),
          labels: [
            { cluster_id: 1, label: 'Morning' },
            { cluster_id: 2, label: 'Evening' },
          ],
        },
      },
    });

    const labels = screen.getAllByText(/Run|Empty/).map((node) => node.textContent?.trim());
    expect(labels).toEqual(['Empty', 'Run']);
  });

  it('filters tag rows to the focused cluster (#592)', () => {
    render(ComparisonHeatmapHarness, {
      props: {
        pruneSparseAxes: false,
        sortMode: 'clustered',
        focusedClusterId: 2,
        clusterMeta: {
          byTagId: new Map([
            ['t1', 2],
            ['t2', 1],
          ]),
          labels: [
            { cluster_id: 1, label: 'Morning' },
            { cluster_id: 2, label: 'Evening' },
          ],
        },
      },
    });

    expect(screen.getByText('Run')).toBeTruthy();
    expect(screen.queryByText('Empty')).toBeNull();
  });
});
