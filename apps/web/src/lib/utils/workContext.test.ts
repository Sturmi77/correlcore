import { describe, expect, it } from 'vitest';
import { defaultWorkContextForDate } from './workContext';

describe('defaultWorkContextForDate', () => {
  it('returns weekend on Saturday and Sunday', () => {
    expect(defaultWorkContextForDate(new Date('2026-05-16T12:00:00'))).toBe('weekend');
    expect(defaultWorkContextForDate(new Date('2026-05-17T12:00:00'))).toBe('weekend');
  });

  it('returns homeoffice on weekdays', () => {
    expect(defaultWorkContextForDate(new Date('2026-05-15T12:00:00'))).toBe('homeoffice');
    expect(defaultWorkContextForDate(new Date('2026-05-13T12:00:00'))).toBe('homeoffice');
  });
});
