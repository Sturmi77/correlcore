import { describe, it, expect } from 'vitest';
import { classifyDateLabel } from './dateLabels';

describe('classifyDateLabel', () => {
  const today = '2026-05-09'; // Saturday

  it('flags today', () => {
    expect(classifyDateLabel('2026-05-09', today)).toEqual({ kind: 'today' });
  });

  it('flags yesterday', () => {
    expect(classifyDateLabel('2026-05-08', today)).toEqual({ kind: 'yesterday' });
  });

  it('returns the weekday key for older dates', () => {
    // 2026-05-07 was a Thursday.
    expect(classifyDateLabel('2026-05-07', today)).toEqual({ kind: 'weekday', weekday: 'thu' });
  });

  it('returns a stable weekday for valid older dates', () => {
    // 2026-05-04 was a Monday.
    expect(classifyDateLabel('2026-05-04', today)).toEqual({ kind: 'weekday', weekday: 'mon' });
  });

  it('falls back to mon for malformed input rather than crashing', () => {
    expect(classifyDateLabel('not-a-date', today)).toEqual({ kind: 'weekday', weekday: 'mon' });
  });
});
