/**
 * Phase-gate + occurrence-floor + median tests for Event-Aligned Small Multiples.
 *
 * The sheet is only safe to render once the insight has reached the
 * provisional or robust phase (ADR-0021). The median trajectory (#810)
 * additionally requires ≥ MIN_SMALL_MULTIPLES_OCCURRENCES episodes (#811).
 */

import { render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import {
  hasEnoughOccurrences,
  isSmallMultiplesUnlocked,
  MIN_SMALL_MULTIPLES_OCCURRENCES,
  SMALL_MULTIPLES_RADIUS,
} from './smallMultiplesGate';
import EventAlignedSmallMultiplesSheet from './EventAlignedSmallMultiplesSheet.svelte';

vi.mock('svelte-i18n', async () => {
  const { readable } = await import('svelte/store');
  return {
    _: readable((key: string, opts?: { values?: Record<string, unknown> }) =>
      opts?.values ? `${key}:${JSON.stringify(opts.values)}` : key
    ),
  };
});

describe('isSmallMultiplesUnlocked (ADR-0021 phase gate)', () => {
  it('blocks the collecting phase', () => {
    expect(isSmallMultiplesUnlocked('collecting')).toBe(false);
  });

  it('blocks the early_patterns phase', () => {
    expect(isSmallMultiplesUnlocked('early_patterns')).toBe(false);
  });

  it('unlocks at provisional', () => {
    expect(isSmallMultiplesUnlocked('provisional')).toBe(true);
  });

  it('unlocks at robust', () => {
    expect(isSmallMultiplesUnlocked('robust')).toBe(true);
  });

  it('blocks when phase is null or undefined', () => {
    expect(isSmallMultiplesUnlocked(null)).toBe(false);
    expect(isSmallMultiplesUnlocked(undefined)).toBe(false);
  });

  it('keeps the window radius at 7 days', () => {
    expect(SMALL_MULTIPLES_RADIUS).toBe(7);
  });
});

describe('hasEnoughOccurrences (#811)', () => {
  it('requires the documented floor of 3 episodes', () => {
    expect(MIN_SMALL_MULTIPLES_OCCURRENCES).toBe(3);
    expect(hasEnoughOccurrences(0)).toBe(false);
    expect(hasEnoughOccurrences(1)).toBe(false);
    expect(hasEnoughOccurrences(2)).toBe(false);
    expect(hasEnoughOccurrences(3)).toBe(true);
    expect(hasEnoughOccurrences(5)).toBe(true);
  });
});

describe('EventAlignedSmallMultiplesSheet lag marker (#488)', () => {
  const points = [
    {
      period_start: '2026-05-10',
      period_end: '2026-05-10',
      entry_count: 1,
      mood_avg: 4,
      energy_avg: 3,
      stress_avg: 2,
      sleep_quality_avg: null,
    },
    {
      period_start: '2026-05-12',
      period_end: '2026-05-12',
      entry_count: 1,
      mood_avg: 2,
      energy_avg: 3,
      stress_avg: 4,
      sleep_quality_avg: null,
    },
  ];
  const events = [{ onset: '2026-05-10', label: 'Cycling' }];

  it('highlights the +lag_days column and shows the lag note', () => {
    render(EventAlignedSmallMultiplesSheet, {
      props: { open: true, phase: 'provisional', events, points, metric: 'mood_avg', lagOffset: 2 },
    });

    expect(screen.getByTestId('esm-lag-band')).toBeTruthy();
    const note = screen.getByTestId('esm-lag-note');
    expect(note.textContent).toContain('trends.esm.lag_hint');
    expect(note.textContent).toContain('"days":2');
  });

  it('omits the lag marker for co-occurrence insights (lagOffset null)', () => {
    render(EventAlignedSmallMultiplesSheet, {
      props: {
        open: true,
        phase: 'provisional',
        events,
        points,
        metric: 'mood_avg',
        lagOffset: null,
      },
    });

    expect(screen.queryByTestId('esm-lag-band')).toBeNull();
    expect(screen.queryByTestId('esm-lag-note')).toBeNull();
  });

  it('renders intro, metric label, axis caption and colour legend (#631)', () => {
    render(EventAlignedSmallMultiplesSheet, {
      props: {
        open: true,
        phase: 'provisional',
        events,
        points,
        metric: 'energy_avg',
        lagOffset: null,
      },
    });

    expect(screen.getByTestId('esm-intro').textContent).toContain('trends.esm.body');
    expect(screen.getByTestId('esm-metric-label').textContent).toContain('trends.esm.metric_label');
    expect(screen.getByTestId('esm-axis-caption').textContent).toBe('trends.esm.axis_caption');
    expect(screen.getByTestId('esm-legend').textContent).toContain('trends.esm.legend_worse');
    expect(screen.getByTestId('esm-legend').textContent).toContain('trends.esm.legend_better');
  });

  it('labels the legend by well-being direction so it stays correct for inverted metrics like stress (#631)', () => {
    render(EventAlignedSmallMultiplesSheet, {
      props: {
        open: true,
        phase: 'provisional',
        events,
        points,
        metric: 'stress_avg',
        lagOffset: null,
      },
    });

    const legend = screen.getByTestId('esm-legend').textContent ?? '';
    expect(legend).toContain('trends.esm.legend_worse');
    expect(legend).toContain('trends.esm.legend_better');
    expect(legend).not.toContain('trends.esm.legend_low');
    expect(legend).not.toContain('trends.esm.legend_high');
  });
});

describe('EventAlignedSmallMultiplesSheet occurrence floor + median (#810/#811)', () => {
  const points = [
    {
      period_start: '2026-05-01',
      period_end: '2026-05-01',
      entry_count: 1,
      mood_avg: 2,
      energy_avg: 3,
      stress_avg: 3,
      sleep_quality_avg: null,
    },
    {
      period_start: '2026-05-10',
      period_end: '2026-05-10',
      entry_count: 1,
      mood_avg: 4,
      energy_avg: 3,
      stress_avg: 2,
      sleep_quality_avg: null,
    },
    {
      period_start: '2026-05-20',
      period_end: '2026-05-20',
      entry_count: 1,
      mood_avg: 3,
      energy_avg: 3,
      stress_avg: 3,
      sleep_quality_avg: null,
    },
  ];

  it('shows need-more hint and hides median when fewer than 3 episodes', () => {
    render(EventAlignedSmallMultiplesSheet, {
      props: {
        open: true,
        phase: 'provisional',
        events: [
          { onset: '2026-05-01', label: 'A' },
          { onset: '2026-05-10', label: 'B' },
        ],
        points,
        metric: 'mood_avg',
        lagOffset: null,
      },
    });

    expect(screen.getByTestId('esm-need-more').textContent).toContain('trends.esm.need_more');
    expect(screen.queryByTestId('esm-median-row')).toBeNull();
    expect(screen.queryByTestId('esm-median-hint')).toBeNull();
  });

  it('renders the median trajectory once there are ≥ 3 episodes', () => {
    render(EventAlignedSmallMultiplesSheet, {
      props: {
        open: true,
        phase: 'provisional',
        events: [
          { onset: '2026-05-01', label: 'A' },
          { onset: '2026-05-10', label: 'B' },
          { onset: '2026-05-20', label: 'C' },
        ],
        points,
        metric: 'mood_avg',
        lagOffset: null,
      },
    });

    expect(screen.queryByTestId('esm-need-more')).toBeNull();
    expect(screen.getByTestId('esm-median-row')).toBeTruthy();
    expect(screen.getByTestId('esm-median-hint').textContent).toBe('trends.esm.median_hint');
  });
});

describe('EventAlignedSmallMultiplesSheet partner glyph (#909)', () => {
  const points = [
    {
      period_start: '2026-05-10',
      period_end: '2026-05-10',
      entry_count: 1,
      mood_avg: 4,
      energy_avg: 3,
      stress_avg: 2,
      sleep_quality_avg: null,
    },
    {
      period_start: '2026-05-12',
      period_end: '2026-05-12',
      entry_count: 1,
      mood_avg: 2,
      energy_avg: 3,
      stress_avg: 4,
      sleep_quality_avg: null,
    },
  ];
  const events = [{ onset: '2026-05-10', label: 'Sport' }];
  const candidates = [
    { id: 't-coffee', label: 'Coffee', kind: 'tag' as const, score: 5 },
    { id: 't-sleep', label: 'Sleep', kind: 'tag' as const, score: 2 },
  ];

  it('shows an honest empty state when no partner is available', () => {
    render(EventAlignedSmallMultiplesSheet, {
      props: {
        open: true,
        phase: 'provisional',
        events,
        points,
        metric: 'mood_avg',
        partner: null,
        partnerCandidates: [],
        partnerPresenceDates: [],
      },
    });

    expect(screen.getByTestId('esm-partner-empty')).toBeTruthy();
    expect(screen.queryByTestId('esm-partner-select')).toBeNull();
    expect(screen.queryByTestId('esm-partner-mark')).toBeNull();
  });

  it('overlays at most one partner and marks presence days', () => {
    const { container } = render(EventAlignedSmallMultiplesSheet, {
      props: {
        open: true,
        phase: 'provisional',
        events,
        points,
        metric: 'mood_avg',
        partner: { id: 't-coffee', label: 'Coffee', kind: 'tag' },
        partnerCandidates: candidates,
        partnerPresenceDates: ['2026-05-10', '2026-05-12'],
      },
    });

    expect(screen.getByTestId('esm-partner-select')).toBeTruthy();
    expect(screen.getByTestId('esm-partner-legend').textContent).toContain(
      'trends.esm.partner_legend'
    );
    const marks = container.querySelectorAll('[data-testid="esm-partner-mark"]');
    expect(marks.length).toBe(2);
    expect(container.querySelectorAll('.esm__cell--partner').length).toBe(2);
  });

  it('includes partner-on-day text in cell aria-labels', () => {
    const { container } = render(EventAlignedSmallMultiplesSheet, {
      props: {
        open: true,
        phase: 'provisional',
        events,
        points,
        metric: 'mood_avg',
        partner: { id: 't-coffee', label: 'Coffee', kind: 'tag' },
        partnerCandidates: candidates,
        partnerPresenceDates: ['2026-05-10'],
      },
    });

    const partnerCell = container.querySelector('.esm__cell--partner') as SVGRectElement | null;
    expect(partnerCell?.getAttribute('aria-label')).toContain('trends.esm.partner_on_day');
    expect(partnerCell?.getAttribute('aria-label')).toContain('Coffee');
  });

  it('keeps T0 stroke on partner-hit cells at onset', () => {
    const { container } = render(EventAlignedSmallMultiplesSheet, {
      props: {
        open: true,
        phase: 'provisional',
        events,
        points,
        metric: 'mood_avg',
        partner: { id: 't-coffee', label: 'Coffee', kind: 'tag' },
        partnerCandidates: candidates,
        partnerPresenceDates: ['2026-05-10'],
      },
    });

    const t0PartnerCell = container.querySelector(
      '.esm__cell--t0.esm__cell--partner'
    ) as SVGRectElement | null;
    expect(t0PartnerCell).toBeTruthy();
    expect(t0PartnerCell?.classList.contains('esm__cell--t0')).toBe(true);
  });

  it('keeps the hard max of one active partner in the select options', () => {
    render(EventAlignedSmallMultiplesSheet, {
      props: {
        open: true,
        phase: 'provisional',
        events,
        points,
        metric: 'mood_avg',
        partner: { id: 't-coffee', label: 'Coffee', kind: 'tag' },
        partnerCandidates: candidates,
        partnerPresenceDates: ['2026-05-10'],
      },
    });

    const select = screen.getByTestId('esm-partner-select') as HTMLSelectElement;
    expect(select.options).toHaveLength(2);
    expect(select.value).toBe('t-coffee');
  });
});

describe('EventAlignedSmallMultiplesSheet split medians (#920)', () => {
  // Three windows with the partner, three without, far enough apart that no
  // ±7 window overlaps another onset.
  const withOnsets = ['2026-05-01', '2026-05-20', '2026-06-08'];
  const withoutOnsets = ['2026-07-01', '2026-07-20', '2026-08-08'];
  const events = [...withOnsets, ...withoutOnsets].map((onset) => ({ onset, label: onset }));
  const points = [...withOnsets, ...withoutOnsets].map((date, index) => ({
    period_start: date,
    period_end: date,
    entry_count: 1,
    mood_avg: index < 3 ? 5 : 1,
    energy_avg: 3,
    stress_avg: 3,
    sleep_quality_avg: null,
  }));
  const partner = { id: 't-coffee', label: 'Coffee', kind: 'tag' as const };
  const candidates = [{ id: 't-coffee', label: 'Coffee', kind: 'tag' as const, score: 5 }];

  function renderSheet(partnerPresenceDates: string[]) {
    return render(EventAlignedSmallMultiplesSheet, {
      props: {
        open: true,
        phase: 'provisional',
        events,
        points,
        metric: 'mood_avg',
        partner,
        partnerCandidates: candidates,
        partnerPresenceDates,
      },
    });
  }

  it('replaces the single median with one row per branch', () => {
    const { container } = renderSheet(withOnsets);

    const medianRows = [...container.querySelectorAll('[data-testid="esm-median-row"]')];
    expect(medianRows.map((row) => row.getAttribute('data-branch'))).toEqual(['with', 'without']);
    expect(container.querySelectorAll('[data-testid="esm-split-insufficient"]')).toHaveLength(0);
  });

  it('states the window count of each branch', () => {
    renderSheet(withOnsets);

    const counts = screen.getByTestId('esm-split-counts').textContent ?? '';
    expect(counts).toContain('trends.esm.split_counts');
    expect(counts).toContain('"withCount":3');
    expect(counts).toContain('"withoutCount":3');
  });

  it('withholds the curve of a branch below the occurrence floor', () => {
    // Only two windows carry the partner, so that branch stays undrawn.
    const { container } = renderSheet(withOnsets.slice(0, 2));

    const gap = screen.getByTestId('esm-split-insufficient');
    expect(gap).toBeTruthy();
    expect(gap.parentElement?.getAttribute('data-branch')).toBe('with');
    expect(gap.parentElement?.textContent).toContain('trends.esm.split_insufficient');
    // The other branch still draws, so a gap alone is not a blank sheet.
    expect(container.querySelectorAll('.esm__cell--median').length).toBeGreaterThan(0);
  });

  it('distinguishes the branches by stroke pattern, not by hue', () => {
    const { container } = renderSheet(withOnsets);

    const withoutCells = container.querySelectorAll('.esm__cell--median-without');
    expect(withoutCells.length).toBeGreaterThan(0);
    const withRow = container.querySelector('[data-branch="with"]');
    expect(withRow?.querySelectorAll('.esm__cell--median-without')).toHaveLength(0);
  });

  it('keeps the combined median and points to the split when no partner is set', () => {
    const { container } = render(EventAlignedSmallMultiplesSheet, {
      props: {
        open: true,
        phase: 'provisional',
        events,
        points,
        metric: 'mood_avg',
        partner: null,
        partnerCandidates: candidates,
        partnerPresenceDates: [],
      },
    });

    const medianRows = [...container.querySelectorAll('[data-testid="esm-median-row"]')];
    expect(medianRows).toHaveLength(1);
    expect(medianRows[0]?.getAttribute('data-branch')).toBe('all');
    expect(screen.getByTestId('esm-split-hint')).toBeTruthy();
    expect(screen.queryByTestId('esm-split-counts')).toBeNull();
  });

  it('keeps the branch qualifier readable for a long partner name', () => {
    const { container } = render(EventAlignedSmallMultiplesSheet, {
      props: {
        open: true,
        phase: 'provisional',
        events,
        points,
        metric: 'mood_avg',
        partner: { id: 't-coffee', label: 'Cold brew coffee with oat milk', kind: 'tag' as const },
        partnerCandidates: candidates,
        partnerPresenceDates: withOnsets,
      },
    });

    const labels = [...container.querySelectorAll('.esm__row-label--median')];
    const withLabel = labels[0]?.textContent ?? '';
    const withoutLabel = labels[1]?.textContent ?? '';
    expect(withLabel).toContain('trends.esm.split_with');
    expect(withoutLabel).toContain('trends.esm.split_without');
    // Shortened for the gutter, but the full name stays in the tooltip.
    expect(withLabel).toContain('…');
    expect(labels[0]?.querySelector('title')?.textContent).toContain(
      'Cold brew coffee with oat milk'
    );
  });

  it('withholds the split prompt while no partner can be chosen', () => {
    const base = {
      open: true,
      phase: 'provisional' as const,
      events,
      points,
      metric: 'mood_avg' as const,
      partner: null,
      partnerPresenceDates: [],
    };

    const loading = render(EventAlignedSmallMultiplesSheet, {
      props: { ...base, partnerCandidates: [], partnerLoading: true },
    });
    expect(screen.queryByTestId('esm-split-hint')).toBeNull();
    loading.unmount();

    const failed = render(EventAlignedSmallMultiplesSheet, {
      props: { ...base, partnerCandidates: candidates, partnerUnavailable: true },
    });
    expect(screen.queryByTestId('esm-split-hint')).toBeNull();
    failed.unmount();

    const empty = render(EventAlignedSmallMultiplesSheet, {
      props: { ...base, partnerCandidates: [] },
    });
    expect(screen.queryByTestId('esm-split-hint')).toBeNull();
    empty.unmount();

    render(EventAlignedSmallMultiplesSheet, {
      props: { ...base, partnerCandidates: candidates },
    });
    expect(screen.getByTestId('esm-split-hint')).toBeTruthy();
  });

  it('pushes the episode rows below however many median rows exist', () => {
    const { container } = renderSheet(withOnsets);

    const episodeRows = [...container.querySelectorAll('.esm__row[data-onset]')];
    const firstCellY = episodeRows[0]?.querySelector('.esm__cell')?.getAttribute('y');
    // 24 + 2 median rows * (cellSize 22 + gap 4)
    expect(firstCellY).toBe('76');
  });
});

describe('EventAlignedSmallMultiplesSheet partner coverage (#918)', () => {
  const points = [
    {
      period_start: '2026-05-10',
      period_end: '2026-05-10',
      entry_count: 1,
      mood_avg: 4,
      energy_avg: 3,
      stress_avg: 2,
      sleep_quality_avg: null,
    },
  ];
  // Two windows far enough apart that a ±7 overlap is impossible.
  const events = [
    { onset: '2026-05-10', label: 'Sport' },
    { onset: '2026-06-20', label: 'Sport' },
  ];
  const candidates = [{ id: 't-coffee', label: 'Coffee', kind: 'tag' as const, score: 5 }];
  const partner = { id: 't-coffee', label: 'Coffee', kind: 'tag' as const };

  it('states how many windows the partner reaches', () => {
    render(EventAlignedSmallMultiplesSheet, {
      props: {
        open: true,
        phase: 'provisional',
        events,
        points,
        metric: 'mood_avg',
        partner,
        partnerCandidates: candidates,
        partnerPresenceDates: ['2026-05-09', '2026-05-12'],
      },
    });

    // #920 states the same coverage per branch, so the split line carries it.
    const summary = screen.getByTestId('esm-split-counts').textContent ?? '';
    expect(summary).toContain('"withCount":1');
    expect(summary).toContain('"withoutCount":1');
  });

  it('counts a window once even when the partner appears on several days', () => {
    render(EventAlignedSmallMultiplesSheet, {
      props: {
        open: true,
        phase: 'provisional',
        events,
        points,
        metric: 'mood_avg',
        partner,
        partnerCandidates: candidates,
        partnerPresenceDates: ['2026-05-09', '2026-05-10', '2026-06-21'],
      },
    });

    expect(screen.getByTestId('esm-split-counts').textContent).toContain('"withCount":2');
  });

  it('drops the header coverage line once the split states the same numbers', () => {
    render(EventAlignedSmallMultiplesSheet, {
      props: {
        open: true,
        phase: 'provisional',
        events,
        points,
        metric: 'mood_avg',
        partner,
        partnerCandidates: candidates,
        partnerPresenceDates: ['2026-05-09'],
      },
    });

    expect(screen.getByTestId('esm-split-counts')).toBeTruthy();
    expect(screen.queryByTestId('esm-partner-summary')).toBeNull();
  });

  it('keeps the header coverage line when there is no split to state it', () => {
    render(EventAlignedSmallMultiplesSheet, {
      props: {
        open: true,
        phase: 'provisional',
        events: [],
        points,
        metric: 'mood_avg',
        partner,
        partnerCandidates: candidates,
        partnerPresenceDates: ['2026-05-09'],
      },
    });

    expect(screen.queryByTestId('esm-split-counts')).toBeNull();
    expect(screen.getByTestId('esm-partner-summary').textContent).toContain(
      'trends.esm.partner_summary'
    );
  });

  it('shows a loading state instead of the empty message while the lookup runs', () => {
    render(EventAlignedSmallMultiplesSheet, {
      props: {
        open: true,
        phase: 'provisional',
        events,
        points,
        metric: 'mood_avg',
        partner: null,
        partnerCandidates: [],
        partnerPresenceDates: [],
        partnerLoading: true,
      },
    });

    expect(screen.getByTestId('esm-partner-loading')).toBeTruthy();
    expect(screen.queryByTestId('esm-partner-empty')).toBeNull();
  });

  it('explains a failed presence fetch instead of rendering a silent overlay', () => {
    render(EventAlignedSmallMultiplesSheet, {
      props: {
        open: true,
        phase: 'provisional',
        events,
        points,
        metric: 'mood_avg',
        partner: null,
        partnerCandidates: candidates,
        partnerPresenceDates: [],
        partnerUnavailable: true,
      },
    });

    expect(screen.getByTestId('esm-partner-error')).toBeTruthy();
    expect(screen.queryByTestId('esm-partner-select')).toBeNull();
    expect(screen.queryByTestId('esm-partner-summary')).toBeNull();
  });
});

describe('EventAlignedSmallMultiplesSheet sleep duration (#928 D3)', () => {
  // Sleep is logged in minutes, but the sheet fed those minutes straight into
  // a mapper built for a 1–5 rating scale: every night normalised far past +1,
  // so the whole row rendered identical and told the reader nothing.
  const events = [{ onset: '2026-05-08', label: 'Cycling' }];

  function sleepPoints(minutes: readonly number[]) {
    return minutes.map((value, index) => ({
      period_start: `2026-05-${String(index + 1).padStart(2, '0')}`,
      period_end: `2026-05-${String(index + 1).padStart(2, '0')}`,
      entry_count: 1,
      mood_avg: 3,
      energy_avg: 3,
      stress_avg: 3,
      sleep_quality_avg: null,
      sleep_minutes_avg: value,
    }));
  }

  function loggedCells(container: HTMLElement) {
    return Array.from(container.querySelectorAll('.esm__cell:not(.esm__cell--median)')).filter(
      (cell) => Number(cell.getAttribute('opacity')) > 0
    );
  }

  it('separates short from long nights instead of saturating every cell', () => {
    const minutes = [
      ...Array.from({ length: 7 }, () => 300),
      ...Array.from({ length: 7 }, () => 540),
    ];
    const { container } = render(EventAlignedSmallMultiplesSheet, {
      props: {
        open: true,
        phase: 'provisional',
        events,
        points: sleepPoints(minutes),
        metric: 'sleep_minutes_avg',
        lagOffset: null,
      },
    });

    const signs = new Set(loggedCells(container).map((cell) => cell.getAttribute('data-sign')));
    expect(signs.size).toBeGreaterThan(1);
    expect(signs.has('pos')).toBe(true);
    expect(signs.has('neg')).toBe(true);
  });

  it('names the reference point rather than labelling durations better or worse', () => {
    const minutes = Array.from({ length: 14 }, () => 420);
    render(EventAlignedSmallMultiplesSheet, {
      props: {
        open: true,
        phase: 'provisional',
        events,
        points: sleepPoints(minutes),
        metric: 'sleep_minutes_avg',
        lagOffset: null,
      },
    });

    const legend = screen.getByTestId('esm-legend').textContent ?? '';
    expect(legend).toContain('trends.esm.legend_sleep_shorter');
    expect(legend).toContain('trends.esm.legend_sleep_longer');
    expect(legend).not.toContain('trends.esm.legend_better');
    expect(screen.getByTestId('esm-sleep-basis').textContent).toContain(
      'trends.sleep_scale.baseline'
    );
  });

  it('keeps the well-being legend for the 1–5 metrics', () => {
    render(EventAlignedSmallMultiplesSheet, {
      props: {
        open: true,
        phase: 'provisional',
        events,
        points: sleepPoints([420, 420, 420]),
        metric: 'mood_avg',
        lagOffset: null,
      },
    });

    expect(screen.getByTestId('esm-legend').textContent).toContain('trends.esm.legend_better');
    expect(screen.queryByTestId('esm-sleep-basis')).toBeNull();
  });

  it('reports a cell as a duration, not as a chart position', () => {
    const minutes = Array.from({ length: 14 }, () => 430);
    const { container } = render(EventAlignedSmallMultiplesSheet, {
      props: {
        open: true,
        phase: 'provisional',
        events,
        points: sleepPoints(minutes),
        metric: 'sleep_minutes_avg',
        lagOffset: null,
      },
    });

    // Every night is the same length here, so the divergent encoding leaves the
    // cells transparent — the label still has to say what they stand for.
    const labels = Array.from(container.querySelectorAll('.esm__cell:not(.esm__cell--median)')).map(
      (cell) => cell.getAttribute('aria-label') ?? ''
    );
    expect(labels.some((label) => label.includes('7 h 10 min'))).toBe(true);
  });
});
