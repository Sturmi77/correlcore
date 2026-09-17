import { describe, expect, it } from 'vitest';
import type { CoincidenceRow } from './coincidenceMarkers';
import {
  MIN_LAG1_DAYS,
  deriveLag1,
  hasReportableLag1,
  lag1DaysToMarkers,
  summarizeLag1,
} from './lag1Markers';

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

  it('reports both directions with their opportunity counts', () => {
    expect(summarizeLag1(['t1', 't2'], [sport, sleep])).toEqual([
      {
        from: { id: 't1', label: 'Sport' },
        to: { id: 't2', label: 'Sleep' },
        forward: 3,
        forwardTotal: 3,
        reverse: 2,
        reverseTotal: 3,
      },
    ]);
  });

  it('keeps a zero direction visible instead of dropping it', () => {
    // Coffee only ever follows Sport, never precedes it.
    const coffee = row('t3', 'Coffee', [{ date: '2026-05-06', count: 1 }]);
    const [pair] = summarizeLag1(['t1', 't3'], [sport, coffee]);
    expect(pair?.forward).toBe(1);
    expect(pair?.reverse).toBe(0);
    expect(pair?.reverseTotal).toBe(1);
  });

  it('counts an antecedent day only when its successor is inside the range', () => {
    const axisDates = ['2026-05-01', '2026-05-02', '2026-05-03', '2026-05-04', '2026-05-05'];
    const [pair] = summarizeLag1(['t1', 't2'], [sport, sleep], { axisDates });
    // 2026-05-05 is the last axis day, so it offers no next-day opportunity.
    expect(pair?.forwardTotal).toBe(2);
    expect(pair?.forward).toBe(2);
    // Sleep on 2026-05-06 falls outside the axis entirely.
    expect(pair?.reverseTotal).toBe(2);
    expect(pair?.reverse).toBe(2);
  });

  it('separates a rare direction from a frequent one via the denominator', () => {
    // Sport is active on many days, Coffee on two — bare hit counts would read
    // as "Sport dominates" when the opposite is true.
    const manyDays = Array.from({ length: 10 }, (_, index) => ({
      date: `2026-05-${String(index + 1).padStart(2, '0')}`,
      count: 1,
    }));
    const frequent = row('t1', 'Sport', manyDays);
    const rare = row('t3', 'Coffee', [
      { date: '2026-05-02', count: 1 },
      { date: '2026-05-04', count: 1 },
    ]);
    const [pair] = summarizeLag1(['t1', 't3'], [frequent, rare]);
    expect(pair?.forward).toBe(2);
    expect(pair?.forwardTotal).toBe(10);
    expect(pair?.reverse).toBe(2);
    expect(pair?.reverseTotal).toBe(2);
  });

  it('reports a pair whose reverse direction alone clears the floor', () => {
    // Pinned as Sport→Sleep, but Sleep is what precedes Sport every time, so
    // the pin-order marker gate stays shut while the numbers still say plenty.
    const pinnedFirst = row('t1', 'Sport', [
      { date: '2026-05-02', count: 1 },
      { date: '2026-05-06', count: 1 },
      { date: '2026-05-10', count: 1 },
    ]);
    const pinnedSecond = row('t2', 'Sleep', [
      { date: '2026-05-01', count: 1 },
      { date: '2026-05-05', count: 1 },
      { date: '2026-05-09', count: 1 },
    ]);
    const summaries = summarizeLag1(['t1', 't2'], [pinnedFirst, pinnedSecond]);
    expect(summaries[0]?.forward).toBe(0);
    expect(summaries[0]?.reverse).toBe(3);
    expect(deriveLag1(['t1', 't2'], [pinnedFirst, pinnedSecond]).canHighlight).toBe(false);
    expect(hasReportableLag1(summaries)).toBe(true);
  });

  it('stays quiet when neither direction clears the floor', () => {
    const sparseA = row('t1', 'Sport', [{ date: '2026-05-01', count: 1 }]);
    const sparseB = row('t2', 'Sleep', [{ date: '2026-05-02', count: 1 }]);
    expect(hasReportableLag1(summarizeLag1(['t1', 't2'], [sparseA, sparseB]))).toBe(false);
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
