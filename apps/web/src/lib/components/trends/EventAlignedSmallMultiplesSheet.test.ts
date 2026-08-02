/**
 * Phase-gate tests for the Event-Aligned Small Multiples sheet.
 *
 * The sheet is only safe to render once the insight has reached the
 * provisional or robust phase (ADR-0021). The helper exported from the
 * sheet module is the single source of truth used by both the component
 * and the calling Insight card; both call sites must stay aligned.
 */

import { render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import { isSmallMultiplesUnlocked, SMALL_MULTIPLES_RADIUS } from './smallMultiplesGate';
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
    // The compare panel and any other call site must keep this in sync
    // — it is part of the visual contract documented in ADR-0035 §6.
    expect(SMALL_MULTIPLES_RADIUS).toBe(7);
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
    },
    {
      period_start: '2026-05-12',
      period_end: '2026-05-12',
      entry_count: 1,
      mood_avg: 2,
      energy_avg: 3,
      stress_avg: 4,
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
    // "Worse"/"Better" describe the already-inverted display value (higher =
    // better for every metric), so no metric-specific reversal is needed —
    // unlike "Lower"/"Higher", which described raw stress backwards.
    expect(legend).toContain('trends.esm.legend_worse');
    expect(legend).toContain('trends.esm.legend_better');
    expect(legend).not.toContain('trends.esm.legend_low');
    expect(legend).not.toContain('trends.esm.legend_high');
  });
});
