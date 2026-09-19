/**
 * Tests for calendar ISO date helpers (Phase 1 / #928).
 */

import { describe, it, expect } from 'vitest';
import { localIsoDate, shiftIsoDate } from './isoDate';

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
