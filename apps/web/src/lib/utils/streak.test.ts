/**
 * Tests for streak/avg helpers (ADR-0014).
 *
 * Pure functions over an entries-array — no DOM, no timers needed.
 */

import { describe, it, expect } from 'vitest';
import type { EntryResponse } from '$lib/api/entries';
import {
  averageOver,
  computeEntryStreak,
  countDayEntries,
  localIsoDate,
  shiftIsoDate,
} from './streak';

function entry(date: string, overrides: Partial<EntryResponse> = {}): EntryResponse {
  return {
    id: 'e_' + date,
    user_id: 'u_1',
    entry_date: date,
    slot: 'day',
    mood_score: 3,
    energy: 3,
    stress: 3,
    cycle_day: null,
    work_context: 'homeoffice',
    source: 'direct',
    note: null,
    created_at: date + 'T08:00:00Z',
    updated_at: date + 'T08:00:00Z',
    ...overrides,
  };
}

describe('shiftIsoDate', () => {
  it('walks backwards by one day', () => {
    expect(shiftIsoDate('2026-05-09', -1)).toBe('2026-05-08');
  });
  it('crosses month boundaries', () => {
    expect(shiftIsoDate('2026-05-01', -1)).toBe('2026-04-30');
  });
  it('crosses year boundaries', () => {
    expect(shiftIsoDate('2026-01-01', -1)).toBe('2025-12-31');
  });
  it('handles +1 walk forward too', () => {
    expect(shiftIsoDate('2026-12-31', 1)).toBe('2027-01-01');
  });
});

describe('localIsoDate', () => {
  it('formats a date as YYYY-MM-DD without TZ shift', () => {
    const d = new Date(2026, 4, 9, 23, 59); // 9. May 2026, local time
    expect(localIsoDate(d)).toBe('2026-05-09');
  });
});

describe('computeEntryStreak — coulance for today', () => {
  it('returns 0 for an empty list', () => {
    expect(computeEntryStreak([], '2026-05-09')).toBe(0);
  });

  it('counts consecutive days ending today', () => {
    const e = [entry('2026-05-09'), entry('2026-05-08'), entry('2026-05-07')];
    expect(computeEntryStreak(e, '2026-05-09')).toBe(3);
  });

  it("does not break the streak when today's entry is missing (coulance)", () => {
    // Today empty, but yesterday and the day before have entries.
    const e = [entry('2026-05-08'), entry('2026-05-07')];
    expect(computeEntryStreak(e, '2026-05-09')).toBe(2);
  });

  it('returns 0 if both today and yesterday are missing', () => {
    const e = [entry('2026-05-06'), entry('2026-05-05')];
    expect(computeEntryStreak(e, '2026-05-09')).toBe(0);
  });

  it('stops at the first gap walking backwards', () => {
    // Has 5/9, 5/8, gap, 5/6 — streak = 2
    const e = [entry('2026-05-09'), entry('2026-05-08'), entry('2026-05-06')];
    expect(computeEntryStreak(e, '2026-05-09')).toBe(2);
  });

  it('ignores non-day slot entries', () => {
    const e = [
      entry('2026-05-09'),
      entry('2026-05-08'),
      entry('2026-05-07', { slot: 'morning' as EntryResponse['slot'] }),
    ];
    expect(computeEntryStreak(e, '2026-05-09')).toBe(2);
  });

  it('is robust against duplicate entries for the same day', () => {
    const e = [
      entry('2026-05-09', { id: 'a' }),
      entry('2026-05-09', { id: 'b' }),
      entry('2026-05-08'),
    ];
    expect(computeEntryStreak(e, '2026-05-09')).toBe(2);
  });
});

describe('averageOver', () => {
  it('returns null for an empty list', () => {
    expect(averageOver([], 'mood_score')).toBeNull();
  });

  it('rounds to one decimal place', () => {
    const e = [
      entry('2026-05-09', { mood_score: 3 }),
      entry('2026-05-08', { mood_score: 4 }),
      entry('2026-05-07', { mood_score: 5 }),
    ];
    expect(averageOver(e, 'mood_score')).toBe(4);
  });

  it('handles fractional averages', () => {
    const e = [entry('2026-05-09', { energy: 4 }), entry('2026-05-08', { energy: 3 })];
    expect(averageOver(e, 'energy')).toBe(3.5);
  });

  it('ignores non-day slot entries', () => {
    const e = [
      entry('2026-05-09', { stress: 5 }),
      entry('2026-05-08', { stress: 1, slot: 'evening' as EntryResponse['slot'] }),
    ];
    expect(averageOver(e, 'stress')).toBe(5);
  });

  it('returns null when only non-day entries exist', () => {
    const e = [entry('2026-05-09', { slot: 'morning' as EntryResponse['slot'] })];
    expect(averageOver(e, 'mood_score')).toBeNull();
  });
});

describe('countDayEntries', () => {
  it('counts only slot=day entries', () => {
    const e = [
      entry('2026-05-09'),
      entry('2026-05-08', { slot: 'morning' as EntryResponse['slot'] }),
      entry('2026-05-07'),
    ];
    expect(countDayEntries(e)).toBe(2);
  });
});
