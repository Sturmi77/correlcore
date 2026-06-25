import { describe, expect, it } from 'vitest';
import { isEntryDateEditable, resolveInitialDate } from './entryForm';

const today = new Date(2026, 5, 23, 12);

describe('isEntryDateEditable', () => {
  it('accepts today and the inclusive seven-day boundary', () => {
    expect(isEntryDateEditable(today, '2026-06-23')).toBe(true);
    expect(isEntryDateEditable(today, '2026-06-16')).toBe(true);
  });

  it('rejects older, future, and invalid calendar dates', () => {
    expect(isEntryDateEditable(today, '2026-06-15')).toBe(false);
    expect(isEntryDateEditable(today, '2026-06-24')).toBe(false);
    expect(isEntryDateEditable(today, '2026-02-31')).toBe(false);
  });

  it('uses the same UTC date basis as isoDate', () => {
    const utcEvening = new Date('2026-06-23T23:30:00.000Z');

    expect(isEntryDateEditable(utcEvening, '2026-06-23')).toBe(true);
    expect(isEntryDateEditable(utcEvening, '2026-06-24')).toBe(false);
  });
});

describe('resolveInitialDate', () => {
  it('keeps an editable query date', () => {
    expect(resolveInitialDate(today, '2026-06-20')).toBe('2026-06-20');
  });

  it('falls back to today for a read-only historical date', () => {
    expect(resolveInitialDate(today, '2026-06-01')).toBe('2026-06-23');
  });
});
