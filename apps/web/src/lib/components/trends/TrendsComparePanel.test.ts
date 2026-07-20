import { fireEvent, render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import type { TagHeatmapResponse, TimeseriesPoint } from '$lib/api/stats';
import TrendsComparePanel from './TrendsComparePanel.svelte';

vi.mock('svelte-i18n', async () => {
  const { readable } = await import('svelte/store');

  return {
    _: readable((key: string, opts?: { values?: Record<string, unknown> }) => {
      if (key === 'trends.compare.zoom.status' && opts?.values?.days != null) {
        return `${opts.values.days} days / cell`;
      }
      if (key === 'trends.compare.zoom.coverage' && opts?.values) {
        return `Logged days ${opts.values.active} of ${opts.values.present}`;
      }
      if (key === 'trends.compare.zoom.partial' && opts?.values) {
        return `${opts.values.present} of ${opts.values.size} days`;
      }
      if (key === 'trends.compare.zoom.detail' && opts?.values) {
        return `${opts.values.range} · ${opts.values.coverage}`;
      }
      if (key === 'trends.compare.zoom.cell_tooltip' && opts?.values) {
        return `${opts.values.label}, ${opts.values.range}: ${opts.values.value} · ${opts.values.coverage}`;
      }
      if (key === 'trends.compare.zoom.cell_tooltip_zoom' && opts?.values) {
        return `${opts.values.label}, ${opts.values.range}: ${opts.values.value} · ${opts.values.coverage} · Tap to zoom in`;
      }
      return key;
    }),
  };
});

vi.mock('$app/environment', () => ({
  browser: false,
}));

const enabled = { mood_avg: true, energy_avg: true, stress_avg: true };

function dayPoint(date: string, entry_count = 1): TimeseriesPoint {
  return {
    period_start: date,
    period_end: date,
    entry_count,
    mood_avg: entry_count > 0 ? 3 : null,
    energy_avg: entry_count > 0 ? 4 : null,
    stress_avg: entry_count > 0 ? 2 : null,
  };
}

const pointsWithEntries = [dayPoint('2026-05-01')];

const pointsWithoutEntries = [dayPoint('2026-05-01', 0)];

const tagHeatmap: TagHeatmapResponse = {
  start_date: '2026-05-01',
  end_date: '2026-05-01',
  tags: [
    {
      tag_id: 't1',
      name: 'Sport',
      slug: 'sport',
      category: 'sport',
      color: null,
      days: [{ date: '2026-05-01', count: 1 }],
    },
  ],
};

const weekHeatmap: TagHeatmapResponse = {
  start_date: '2026-05-01',
  end_date: '2026-05-14',
  tags: [
    {
      tag_id: 't1',
      name: 'Sport',
      slug: 'sport',
      category: 'sport',
      color: null,
      days: [
        { date: '2026-05-01', count: 1 },
        { date: '2026-05-08', count: 2 },
      ],
    },
  ],
};

const weekPoints = Array.from({ length: 14 }, (_, index) => {
  const day = String(index + 1).padStart(2, '0');
  return dayPoint(`2026-05-${day}`);
});

describe('TrendsComparePanel', () => {
  it('hides Kontextzeilen when the selected range has no entries', () => {
    const { container } = render(TrendsComparePanel, {
      props: {
        points: pointsWithoutEntries,
        range: 'week',
        enabled,
        tagHeatmap,
        showTags: true,
        loading: false,
        compactChrome: true,
      },
    });

    expect(container.querySelector('.compare-heatmap')).toBeNull();
    expect(screen.queryByText('trends.compare.heatmap_heading')).toBeNull();
  });

  it('shows Kontextzeilen when the selected range has entries', () => {
    const { container } = render(TrendsComparePanel, {
      props: {
        points: pointsWithEntries,
        range: 'week',
        enabled,
        tagHeatmap,
        showTags: true,
        loading: false,
        compactChrome: true,
      },
    });

    expect(container.querySelector('.compare-heatmap')).toBeTruthy();
    expect(screen.getByText('trends.compare.heatmap_heading')).toBeTruthy();
  });

  it('zooms the shared axis for chart and heatmap together', async () => {
    const { container } = render(TrendsComparePanel, {
      props: {
        points: weekPoints,
        range: 'year',
        enabled,
        tagHeatmap: weekHeatmap,
        showTags: true,
        loading: false,
        compactChrome: true,
      },
    });

    expect(screen.getByTestId('trends-compare-zoom')).toBeTruthy();
    // Default stage 2 → 7 days/cell ⇒ 14 days → 2 columns.
    expect(screen.getByTestId('trends-compare-zoom-status').textContent).toContain('7');
    let cells = [...container.querySelectorAll('.compare-heatmap__cell[data-date]')];
    expect(new Set(cells.map((cell) => cell.getAttribute('data-date'))).size).toBe(2);

    await fireEvent.click(screen.getByTestId('trends-compare-zoom-increase'));
    expect(screen.getByTestId('trends-compare-zoom-status').textContent).toContain('3');
    cells = [...container.querySelectorAll('.compare-heatmap__cell[data-date]')];
    expect(new Set(cells.map((cell) => cell.getAttribute('data-date'))).size).toBe(5);

    await fireEvent.click(screen.getByTestId('trends-compare-zoom-increase'));
    expect(screen.getByTestId('trends-compare-zoom-status').textContent).toContain('1');
    cells = [...container.querySelectorAll('.compare-heatmap__cell[data-date]')];
    expect(new Set(cells.map((cell) => cell.getAttribute('data-date'))).size).toBe(14);
  });

  it('zooms in one stage when tapping a multi-day heatmap cell', async () => {
    const selectSpy = vi.fn();
    const { container } = render(TrendsComparePanel, {
      props: {
        points: weekPoints,
        range: 'year',
        enabled,
        tagHeatmap: weekHeatmap,
        showTags: true,
        loading: false,
        compactChrome: true,
      },
      events: { selectDate: selectSpy },
    });

    expect(screen.getByTestId('trends-compare-zoom-encoding')).toBeTruthy();
    expect(screen.getByTestId('trends-compare-zoom-tap-hint')).toBeTruthy();

    const zoomable = container.querySelector(
      '.compare-heatmap__cell[data-zoomable="true"]'
    ) as HTMLButtonElement;
    expect(zoomable).toBeTruthy();
    await fireEvent.click(zoomable);

    expect(screen.getByTestId('trends-compare-zoom-status').textContent).toContain('3');
    expect(selectSpy).not.toHaveBeenCalled();
    const columns = new Set(
      [...container.querySelectorAll('.compare-heatmap__cell[data-date]')].map((cell) =>
        cell.getAttribute('data-date')
      )
    );
    expect(columns.size).toBe(5);
  });

  it('opens the day sheet when tapping a single-day heatmap cell', async () => {
    const selectSpy = vi.fn();
    const { container } = render(TrendsComparePanel, {
      props: {
        points: weekPoints,
        range: 'year',
        enabled,
        tagHeatmap: weekHeatmap,
        showTags: true,
        loading: false,
        compactChrome: true,
      },
      events: { selectDate: selectSpy },
    });

    // Zoom to day columns first.
    await fireEvent.click(screen.getByTestId('trends-compare-zoom-increase'));
    await fireEvent.click(screen.getByTestId('trends-compare-zoom-increase'));
    expect(screen.getByTestId('trends-compare-zoom-status').textContent).toContain('1');

    const dayCell = container.querySelector(
      '.compare-heatmap__cell[data-date="2026-05-08"]'
    ) as HTMLButtonElement;
    expect(dayCell?.getAttribute('data-zoomable')).toBe('false');
    await fireEvent.click(dayCell);

    expect(selectSpy).toHaveBeenCalledTimes(1);
    expect(selectSpy.mock.calls[0]?.[0]?.detail?.date).toBe('2026-05-08');
    expect(screen.getByTestId('trends-compare-zoom-status').textContent).toContain('1');
  });
});
