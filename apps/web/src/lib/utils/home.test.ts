/**
 * Tests for Home-Screen helpers (Issue #97).
 */

import { describe, expect, it } from 'vitest';
import type { EntryResponse } from '$lib/api/entries';
import { findEntryForDate, formatHomeDate, greetingKey, localIsoDate } from './home';

describe('localIsoDate', () => {
  it('formats year/month/day with zero-padding in local time', () => {
    const d = new Date(2026, 0, 7, 23, 59, 59); // 7 Jan 2026, local
    expect(localIsoDate(d)).toBe('2026-01-07');
  });

  it('does not roll over due to UTC offset (regression vs toISOString)', () => {
    // 1 May 2026 23:30 local — toISOString() in UTC+ might yield "2026-05-02".
    const d = new Date(2026, 4, 1, 23, 30, 0);
    expect(localIsoDate(d)).toBe('2026-05-01');
  });
});

describe('greetingKey', () => {
  it('returns morning between 05:00 and 11:59', () => {
    expect(greetingKey(5)).toBe('home.greeting_morning');
    expect(greetingKey(8)).toBe('home.greeting_morning');
    expect(greetingKey(11)).toBe('home.greeting_morning');
  });

  it('returns day between 12:00 and 17:59', () => {
    expect(greetingKey(12)).toBe('home.greeting_day');
    expect(greetingKey(15)).toBe('home.greeting_day');
    expect(greetingKey(17)).toBe('home.greeting_day');
  });

  it('returns evening from 18:00 through 04:59 (across midnight)', () => {
    expect(greetingKey(18)).toBe('home.greeting_evening');
    expect(greetingKey(22)).toBe('home.greeting_evening');
    expect(greetingKey(0)).toBe('home.greeting_evening');
    expect(greetingKey(4)).toBe('home.greeting_evening');
  });
});

describe('findEntryForDate', () => {
  const make = (date: string): EntryResponse => ({
    id: `e-${date}`,
    user_id: 'u1',
    entry_date: date,
    slot: 'day',
    mood_score: 3,
    energy: 3,
    stress: 3,
    cycle_day: null,
    work_context: 'homeoffice',
    source: 'direct',
    note: null,
    created_at: '2026-05-07T10:00:00Z',
    updated_at: '2026-05-07T10:00:00Z',
  });

  it('returns null for empty / nullish input', () => {
    expect(findEntryForDate([], '2026-05-07')).toBeNull();
    expect(findEntryForDate(null, '2026-05-07')).toBeNull();
    expect(findEntryForDate(undefined, '2026-05-07')).toBeNull();
  });

  it('returns the entry whose entry_date matches', () => {
    const entries = [make('2026-05-06'), make('2026-05-07'), make('2026-05-05')];
    const hit = findEntryForDate(entries, '2026-05-07');
    expect(hit).not.toBeNull();
    expect(hit?.id).toBe('e-2026-05-07');
  });

  it('returns null when no entry matches', () => {
    const entries = [make('2026-05-06'), make('2026-05-05')];
    expect(findEntryForDate(entries, '2026-05-07')).toBeNull();
  });

  it('ignores non-day slots for the same date', () => {
    const entries = [{ ...make('2026-05-07'), slot: 'evening' as const }];
    expect(findEntryForDate(entries, '2026-05-07')).toBeNull();
  });
});

describe('formatHomeDate', () => {
  it('formats a long weekday date', () => {
    const label = formatHomeDate('2026-05-15', 'en');
    expect(label).toMatch(/2026|15|May/i);
  });
});
