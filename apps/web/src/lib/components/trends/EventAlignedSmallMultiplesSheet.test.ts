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

    const summary = screen.getByTestId('esm-partner-summary').textContent ?? '';
    expect(summary).toContain('trends.esm.partner_summary');
    expect(summary).toContain('"hits":1');
    expect(summary).toContain('"windows":2');
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

    expect(screen.getByTestId('esm-partner-summary').textContent).toContain('"hits":2');
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
