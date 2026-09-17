import { fireEvent, render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import type { TagHeatmapResponse, TimeseriesPoint } from '$lib/api/stats';
import TrendsComparePanel from './TrendsComparePanel.svelte';

vi.mock('svelte-i18n', async () => {
  const { readable } = await import('svelte/store');
  // Join segments so gitleaks does not treat dotted i18n keys as API secrets.
  const k = (...parts: string[]) => parts.join('.');

  return {
    _: readable((key: string, opts?: { values?: Record<string, unknown> }) => {
      if (key === k('trends', 'compare', 'zoom', 'status') && opts?.values?.days != null) {
        return `${opts.values.days} days / cell`;
      }
      if (key === k('trends', 'compare', 'zoom', 'coverage') && opts?.values) {
        return `Logged days ${opts.values.active} of ${opts.values.present}`;
      }
      if (key === k('trends', 'compare', 'zoom', 'partial') && opts?.values) {
        return `${opts.values.present} of ${opts.values.size} days`;
      }
      if (key === k('trends', 'compare', 'zoom', 'detail') && opts?.values) {
        return `${opts.values.range} · ${opts.values.coverage}`;
      }
      if (key === k('trends', 'compare', 'zoom', 'cell_tooltip') && opts?.values) {
        return `${opts.values.label}, ${opts.values.range}: ${opts.values.value} · ${opts.values.coverage}`;
      }
      if (key === k('trends', 'compare', 'zoom', 'cell_tooltip_zoom') && opts?.values) {
        return `${opts.values.label}, ${opts.values.range}: ${opts.values.value} · ${opts.values.coverage} · Tap to zoom in`;
      }
      if (key === k('trends', 'compare', 'coincidence', 'empty') && opts?.values?.min != null) {
        return `Need at least ${opts.values.min} shared days`;
      }
      if (
        key === k('trends', 'compare', 'coincidence', 'cursor') &&
        opts?.values?.subjects != null
      ) {
        return `${opts.values.subjects} on this day`;
      }
      if (
        key === k('trends', 'compare', 'coincidence', 'marker') &&
        opts?.values?.subjects != null
      ) {
        return `Coincidence: ${opts.values.subjects}`;
      }
      if (key === k('trends', 'compare', 'coincidence', 'and')) return 'and';
      if (key === k('trends', 'compare', 'lag1', 'empty') && opts?.values?.min != null) {
        return `Need at least ${opts.values.min} next-day sequences`;
      }
      if (key === k('trends', 'compare', 'lag1', 'cursor') && opts?.values) {
        return `${opts.values.from} then ${opts.values.to} (+1 day)`;
      }
      if (key === k('trends', 'compare', 'lag1', 'marker') && opts?.values) {
        return `Sequence: ${opts.values.from} → ${opts.values.to} (+1d)`;
      }
      return key;
    }),
  };
});

vi.mock('$app/environment', () => ({
  browser: false,
}));

const enabled = { mood_avg: true, energy_avg: true, stress_avg: true, sleep_quality_avg: false };

function dayPoint(date: string, entry_count = 1): TimeseriesPoint {
  return {
    period_start: date,
    period_end: date,
    entry_count,
    mood_avg: entry_count > 0 ? 3 : null,
    energy_avg: entry_count > 0 ? 4 : null,
    stress_avg: entry_count > 0 ? 2 : null,
    sleep_quality_avg: null,
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

const coincidenceHeatmap: TagHeatmapResponse = {
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
        { date: '2026-05-03', count: 1 },
        { date: '2026-05-08', count: 1 },
      ],
    },
    {
      tag_id: 't2',
      name: 'Sleep',
      slug: 'sleep',
      category: 'health',
      color: null,
      days: [
        { date: '2026-05-01', count: 1 },
        { date: '2026-05-03', count: 1 },
        { date: '2026-05-09', count: 1 },
      ],
    },
  ],
};

const sparseCoincidenceHeatmap: TagHeatmapResponse = {
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
        { date: '2026-05-08', count: 1 },
      ],
    },
    {
      tag_id: 't2',
      name: 'Sleep',
      slug: 'sleep',
      category: 'health',
      color: null,
      days: [{ date: '2026-05-01', count: 1 }],
    },
  ],
};

async function pinAllRows(container: HTMLElement): Promise<void> {
  const pins = [...container.querySelectorAll('.compare-heatmap__pin')] as HTMLButtonElement[];
  for (const pin of pins) {
    if (pin.getAttribute('aria-pressed') !== 'true') {
      await fireEvent.click(pin);
    }
  }
}

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

  it('keeps the zoom stage and controls when switching to Strips (#482)', async () => {
    render(TrendsComparePanel, {
      props: {
        points: weekPoints,
        range: 'year',
        enabled,
        tagHeatmap: weekHeatmap,
        showTags: true,
        loading: false,
        compactChrome: false,
      },
    });

    expect(screen.getByTestId('trends-compare-zoom-status').textContent).toContain('7');

    await fireEvent.click(screen.getByRole('button', { name: 'trends.compare.mode_strips' }));

    // #482: Strips share the Lines bucket aggregation, so the zoom stage carries
    // across modes instead of resetting to 1 day/cell.
    expect(screen.getByTestId('trends-compare-zoom-status').textContent).toContain('7');
    expect(screen.getByTestId('unified-strip-chart')).toBeTruthy();
    // Zoom controls stay usable in strip mode.
    expect((screen.getByTestId('trends-compare-zoom-decrease') as HTMLButtonElement).disabled).toBe(
      false
    );
    expect((screen.getByTestId('trends-compare-zoom-increase') as HTMLButtonElement).disabled).toBe(
      false
    );
    // The legacy strip gate / disabled hints are gone.
    expect(screen.queryByTestId('trends-compare-zoom-strip-gate')).toBeNull();
    expect(screen.queryByTestId('trends-compare-zoom-strips-disabled')).toBeNull();
  });

  it('disables coincidence toggle until two pins share enough days (#908)', async () => {
    const { container } = render(TrendsComparePanel, {
      props: {
        points: weekPoints,
        range: 'year',
        enabled,
        tagHeatmap: sparseCoincidenceHeatmap,
        showTags: true,
        loading: false,
        compactChrome: true,
      },
    });

    const toggle = screen.getByTestId('trends-compare-coincidence-toggle') as HTMLInputElement;
    expect(toggle.disabled).toBe(true);
    expect(screen.getByTestId('trends-compare-coincidence-empty').textContent).toContain(
      'trends.compare.coincidence.need_pins'
    );

    await pinAllRows(container);

    expect(toggle.disabled).toBe(true);
    expect(screen.getByTestId('trends-compare-coincidence-empty').textContent).toContain(
      'Need at least 2 shared days'
    );
    expect(container.querySelectorAll('.compare-heatmap__cell--marker-band')).toHaveLength(0);
  });

  it('enables coincidence bands for pinned A∩B days and lists subjects on the cursor (#908)', async () => {
    const { tick } = await import('svelte');
    const { timelineCursor } = await import('$lib/stores/timelineCursor');
    const { container } = render(TrendsComparePanel, {
      props: {
        points: weekPoints,
        range: 'year',
        enabled,
        tagHeatmap: coincidenceHeatmap,
        showTags: true,
        loading: false,
        compactChrome: true,
      },
    });

    await pinAllRows(container);

    const toggle = screen.getByTestId('trends-compare-coincidence-toggle') as HTMLInputElement;
    expect(toggle.disabled).toBe(false);
    expect(screen.queryByTestId('trends-compare-coincidence-empty')).toBeNull();

    await fireEvent.click(toggle);
    expect(toggle.checked).toBe(true);
    expect(screen.getByTestId('trends-compare-coincidence-legend')).toBeTruthy();

    // Zoom to day columns so marker bands map to individual dates.
    await fireEvent.click(screen.getByTestId('trends-compare-zoom-increase'));
    await fireEvent.click(screen.getByTestId('trends-compare-zoom-increase'));
    await tick();

    const bandDates = [...container.querySelectorAll('.compare-heatmap__cell--marker-band')].map(
      (cell) => cell.getAttribute('data-date')
    );
    expect(new Set(bandDates)).toEqual(new Set(['2026-05-01', '2026-05-03']));

    timelineCursor.setDate('2026-05-01', 'tap');
    await tick();
    // Subjects follow pin order (heatmap row order when pinning all).
    expect(screen.getByTestId('trends-compare-coincidence-detail').textContent).toMatch(
      /^(Sport and Sleep|Sleep and Sport) on this day$/
    );
  });

  it('disables Lag-1 toggle until enough A→B +1d days exist (#910)', async () => {
    const sparseLagHeatmap: TagHeatmapResponse = {
      start_date: '2026-05-01',
      end_date: '2026-05-14',
      tags: [
        {
          tag_id: 't1',
          name: 'Sport',
          slug: 'sport',
          category: 'sport',
          color: null,
          days: [{ date: '2026-05-01', count: 1 }],
        },
        {
          tag_id: 't2',
          name: 'Sleep',
          slug: 'sleep',
          category: 'health',
          color: null,
          days: [{ date: '2026-05-02', count: 1 }],
        },
      ],
    };

    const { container } = render(TrendsComparePanel, {
      props: {
        points: weekPoints,
        range: 'year',
        enabled,
        tagHeatmap: sparseLagHeatmap,
        showTags: true,
        loading: false,
        compactChrome: true,
      },
    });

    const toggle = screen.getByTestId('trends-compare-lag1-toggle') as HTMLInputElement;
    expect(toggle.disabled).toBe(true);

    await pinAllRows(container);
    expect(toggle.disabled).toBe(true);
    expect(screen.getByTestId('trends-compare-lag1-empty').textContent).toContain(
      'Need at least 2 next-day sequences'
    );
  });

  it('enables Lag-1 line markers separately from coincidence bands (#910)', async () => {
    const { tick } = await import('svelte');
    const { timelineCursor } = await import('$lib/stores/timelineCursor');
    const lagHeatmap: TagHeatmapResponse = {
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
            { date: '2026-05-03', count: 1 },
            { date: '2026-05-08', count: 1 },
          ],
        },
        {
          tag_id: 't2',
          name: 'Sleep',
          slug: 'sleep',
          category: 'health',
          color: null,
          days: [
            { date: '2026-05-02', count: 1 },
            { date: '2026-05-04', count: 1 },
            { date: '2026-05-09', count: 1 },
          ],
        },
      ],
    };

    const { container } = render(TrendsComparePanel, {
      props: {
        points: weekPoints,
        range: 'year',
        enabled,
        tagHeatmap: lagHeatmap,
        showTags: true,
        loading: false,
        compactChrome: true,
      },
    });

    const pins = [...container.querySelectorAll('.compare-heatmap__pin')] as HTMLButtonElement[];
    // Pin Sport then Sleep so Lag-1 uses Sport→Sleep (+1d), independent of sort order.
    const sportPin = pins.find((button) => button.parentElement?.textContent?.includes('Sport'));
    const sleepPin = pins.find((button) => button.parentElement?.textContent?.includes('Sleep'));
    expect(sportPin && sleepPin).toBeTruthy();
    await fireEvent.click(sportPin!);
    await fireEvent.click(sleepPin!);

    const lagToggle = screen.getByTestId('trends-compare-lag1-toggle') as HTMLInputElement;
    expect(lagToggle.disabled).toBe(false);
    await fireEvent.click(lagToggle);
    expect(lagToggle.checked).toBe(true);
    expect(screen.getByTestId('trends-compare-lag1-legend')).toBeTruthy();

    await fireEvent.click(screen.getByTestId('trends-compare-zoom-increase'));
    await fireEvent.click(screen.getByTestId('trends-compare-zoom-increase'));
    await tick();

    // Lag-1 uses line markers (no endDate) → heatmap marker cells, not soft bands.
    const lineDates = [...container.querySelectorAll('.compare-heatmap__cell--marker')].map(
      (cell) => cell.getAttribute('data-date')
    );
    expect(new Set(lineDates)).toEqual(new Set(['2026-05-01', '2026-05-03', '2026-05-08']));
    expect(container.querySelectorAll('.compare-heatmap__cell--marker-band')).toHaveLength(0);

    timelineCursor.setDate('2026-05-01', 'tap');
    await tick();
    expect(screen.getByTestId('trends-compare-lag1-detail').textContent).toBe(
      'Sport then Sleep (+1 day)'
    );
  });
});
