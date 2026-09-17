import { describe, expect, it } from 'vitest';
import type { CoincidenceRow } from './coincidenceMarkers';
import { MIN_LAG1_DAYS, deriveLag1, lag1DaysToMarkers, summarizeLag1 } from './lag1Markers';

function row(id: string, label: string, days: { date: string; count: number }[]): CoincidenceRow {
  return { id, label, days };
}

describe('deriveLag1', () => {
  const sport = row('t1', 'Sport', [
    { date: '2026-05-01', count: 1 },
    { date: '2026-05-03', count: 1 },
    { date: '2026-05-05', count: 1 },
  ]);
  const sleep = row('t2', 'Sleep', [
    { date: '2026-05-02', count: 1 },
    { date: '2026-05-04', count: 1 },
    { date: '2026-05-06', count: 1 },
  ]);

  it('returns empty when fewer than two pins resolve', () => {
    expect(deriveLag1(['t1'], [sport, sleep])).toEqual({ days: [], canHighlight: false });
  });

  it('marks A→B +1d days in pin order', () => {
    const result = deriveLag1(['t1', 't2'], [sport, sleep]);
    expect(result.days).toEqual([
      {
        date: '2026-05-01',
        sequences: [{ from: { id: 't1', label: 'Sport' }, to: { id: 't2', label: 'Sleep' } }],
      },
      {
        date: '2026-05-03',
        sequences: [{ from: { id: 't1', label: 'Sport' }, to: { id: 't2', label: 'Sleep' } }],
      },
      {
        date: '2026-05-05',
        sequences: [{ from: { id: 't1', label: 'Sport' }, to: { id: 't2', label: 'Sleep' } }],
      },
    ]);
    expect(result.canHighlight).toBe(true);
  });

  it('does not mark same-day co-occurrence as Lag-1', () => {
    const sameDay = row('t2', 'Sleep', [{ date: '2026-05-01', count: 1 }]);
    const result = deriveLag1(['t1', 't2'], [sport, sameDay]);
    expect(result.days).toEqual([]);
    expect(result.canHighlight).toBe(false);
  });

  it('gates canHighlight when Lag-1 days < MIN_LAG1_DAYS', () => {
    const sparseSleep = row('t2', 'Sleep', [{ date: '2026-05-02', count: 1 }]);
    const result = deriveLag1(['t1', 't2'], [sport, sparseSleep]);
    expect(result.days).toHaveLength(1);
    expect(result.canHighlight).toBe(false);
    expect(MIN_LAG1_DAYS).toBe(2);
  });

  it('uses adjacent pairs when three rows are pinned', () => {
    const coffee = row('t3', 'Coffee', [
      { date: '2026-05-03', count: 1 },
      { date: '2026-05-05', count: 1 },
    ]);
    const result = deriveLag1(['t1', 't2', 't3'], [sport, sleep, coffee]);
    // A→B on Sport days; B→C when Sleep is followed by Coffee next day.
    expect(result.days.find((day) => day.date === '2026-05-01')?.sequences).toEqual([
      { from: { id: 't1', label: 'Sport' }, to: { id: 't2', label: 'Sleep' } },
    ]);
    expect(result.days.find((day) => day.date === '2026-05-02')?.sequences).toEqual([
      { from: { id: 't2', label: 'Sleep' }, to: { id: 't3', label: 'Coffee' } },
    ]);
    expect(result.days.find((day) => day.date === '2026-05-03')?.sequences).toEqual([
      { from: { id: 't1', label: 'Sport' }, to: { id: 't2', label: 'Sleep' } },
    ]);
    expect(result.days.find((day) => day.date === '2026-05-04')?.sequences).toEqual([
      { from: { id: 't2', label: 'Sleep' }, to: { id: 't3', label: 'Coffee' } },
    ]);
  });

  it('respects a custom minDays override', () => {
    const sparseSleep = row('t2', 'Sleep', [{ date: '2026-05-02', count: 1 }]);
    expect(deriveLag1(['t1', 't2'], [sport, sparseSleep], { minDays: 1 }).canHighlight).toBe(true);
  });
});

describe('summarizeLag1 (#917)', () => {
  // Sport → Sleep on 3 days; Sleep → Sport on 2 days: the asymmetry markers hide.
  const sport = row('t1', 'Sport', [
    { date: '2026-05-01', count: 1 },
    { date: '2026-05-03', count: 1 },
    { date: '2026-05-05', count: 1 },
  ]);
  const sleep = row('t2', 'Sleep', [
    { date: '2026-05-02', count: 1 },
    { date: '2026-05-04', count: 1 },
    { date: '2026-05-06', count: 1 },
  ]);

  it('returns nothing when fewer than two pins resolve', () => {
    expect(summarizeLag1(['t1'], [sport, sleep])).toEqual([]);
  });

  it('reports both directions for the pinned pair', () => {
    expect(summarizeLag1(['t1', 't2'], [sport, sleep])).toEqual([
      {
        from: { id: 't1', label: 'Sport' },
        to: { id: 't2', label: 'Sleep' },
        forward: 3,
        reverse: 2,
      },
    ]);
  });

  it('keeps a zero direction visible instead of dropping it', () => {
    // Coffee only ever follows Sport, never precedes it.
    const coffee = row('t3', 'Coffee', [{ date: '2026-05-06', count: 1 }]);
    const [pair] = summarizeLag1(['t1', 't3'], [sport, coffee]);
    expect(pair?.forward).toBe(1);
    expect(pair?.reverse).toBe(0);
  });

  it('summarizes the same adjacent pairs the markers use', () => {
    const coffee = row('t3', 'Coffee', [
      { date: '2026-05-03', count: 1 },
      { date: '2026-05-05', count: 1 },
    ]);
    const summaries = summarizeLag1(['t1', 't2', 't3'], [sport, sleep, coffee]);
    expect(summaries.map((pair) => [pair.from.id, pair.to.id])).toEqual([
      ['t1', 't2'],
      ['t2', 't3'],
    ]);
  });
});

describe('lag1DaysToMarkers', () => {
  it('emits narrow line markers (no endDate) with compare_lag1 kind', () => {
    const markers = lag1DaysToMarkers(
      [
        {
          date: '2026-05-01',
          sequences: [
            {
              from: { id: 't1', label: 'Sport' },
              to: { id: 't2', label: 'Sleep' },
            },
          ],
        },
      ],
      (from, to) => `Sequence: ${from} → ${to} (+1d)`,
      'Association only'
    );
    expect(markers).toEqual([
      {
        date: '2026-05-01',
        kind: 'compare_lag1',
        label: 'Sequence: Sport → Sleep (+1d)',
        description: 'Association only',
      },
    ]);
    expect(markers[0]?.endDate).toBeUndefined();
  });
});
