import { describe, expect, it } from 'vitest';
import {
  MAX_COMPARE_PINS,
  MIN_COINCIDENCE_DAYS,
  canPinMore,
  clampPinnedIds,
  coincidenceDaysToMarkers,
  deriveCoincidence,
  isRowActiveOnDay,
  type CoincidenceRow,
} from './coincidenceMarkers';

function row(
  id: string,
  label: string,
  days: { date: string; count: number; max_intensity?: number }[]
): CoincidenceRow {
  return { id, label, days };
}

describe('isRowActiveOnDay', () => {
  it('treats count > 0 as active', () => {
    const sport = row('t1', 'Sport', [{ date: '2026-05-01', count: 1 }]);
    expect(isRowActiveOnDay(sport, '2026-05-01')).toBe(true);
    expect(isRowActiveOnDay(sport, '2026-05-02')).toBe(false);
  });

  it('treats symptom max_intensity > 0 as active even when count is 0', () => {
    const headache = row('s1', 'Headache', [{ date: '2026-05-01', count: 0, max_intensity: 2 }]);
    expect(isRowActiveOnDay(headache, '2026-05-01')).toBe(true);
  });
});

describe('deriveCoincidence', () => {
  const sport = row('t1', 'Sport', [
    { date: '2026-05-01', count: 1 },
    { date: '2026-05-03', count: 1 },
    { date: '2026-05-05', count: 1 },
  ]);
  const sleep = row('t2', 'Sleep', [
    { date: '2026-05-01', count: 1 },
    { date: '2026-05-02', count: 1 },
    { date: '2026-05-05', count: 2 },
  ]);
  const work = row('wc:office', 'Office', [{ date: '2026-05-01', count: 1 }]);

  it('returns empty when fewer than two pins resolve', () => {
    expect(deriveCoincidence(['t1'], [sport, sleep])).toEqual({
      days: [],
      canHighlight: false,
    });
    expect(deriveCoincidence(['t1', 'missing'], [sport, sleep])).toEqual({
      days: [],
      canHighlight: false,
    });
  });

  it('lists A∩B days with both subjects in pin order', () => {
    const result = deriveCoincidence(['t2', 't1'], [sport, sleep]);
    expect(result.days).toEqual([
      {
        date: '2026-05-01',
        subjects: [
          { id: 't2', label: 'Sleep' },
          { id: 't1', label: 'Sport' },
        ],
      },
      {
        date: '2026-05-05',
        subjects: [
          { id: 't2', label: 'Sleep' },
          { id: 't1', label: 'Sport' },
        ],
      },
    ]);
    expect(result.canHighlight).toBe(true);
  });

  it('gates canHighlight when coincidence days < MIN_COINCIDENCE_DAYS', () => {
    const sparseSleep = row('t2', 'Sleep', [{ date: '2026-05-01', count: 1 }]);
    const result = deriveCoincidence(['t1', 't2'], [sport, sparseSleep]);
    expect(result.days).toHaveLength(1);
    expect(result.canHighlight).toBe(false);
    expect(MIN_COINCIDENCE_DAYS).toBe(2);
  });

  it('includes a third pinned row on triple-overlap days only', () => {
    const result = deriveCoincidence(['t1', 't2', 'wc:office'], [sport, sleep, work]);
    expect(result.days.find((day) => day.date === '2026-05-01')?.subjects).toHaveLength(3);
    expect(result.days.find((day) => day.date === '2026-05-05')?.subjects).toHaveLength(2);
  });

  it('respects a custom minDays override', () => {
    const sparseSleep = row('t2', 'Sleep', [{ date: '2026-05-01', count: 1 }]);
    const result = deriveCoincidence(['t1', 't2'], [sport, sparseSleep], { minDays: 1 });
    expect(result.canHighlight).toBe(true);
  });
});

describe('coincidenceDaysToMarkers', () => {
  it('emits soft-band markers (endDate set) with caller labels', () => {
    const markers = coincidenceDaysToMarkers(
      [
        {
          date: '2026-05-01',
          subjects: [
            { id: 't1', label: 'Sport' },
            { id: 't2', label: 'Sleep' },
          ],
        },
      ],
      (labels) => `Coincidence: ${labels.join(' · ')}`,
      'Association only'
    );
    expect(markers).toEqual([
      {
        date: '2026-05-01',
        endDate: '2026-05-01',
        kind: 'generic',
        label: 'Coincidence: Sport · Sleep',
        description: 'Association only',
      },
    ]);
  });
});

describe('pin helpers', () => {
  it('clamps to MAX_COMPARE_PINS', () => {
    expect(MAX_COMPARE_PINS).toBe(3);
    expect(clampPinnedIds(['a', 'b', 'c', 'd'])).toEqual(['a', 'b', 'c']);
    expect(canPinMore(2)).toBe(true);
    expect(canPinMore(3)).toBe(false);
  });
});
