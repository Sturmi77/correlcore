import { describe, expect, it } from 'vitest';
import { isEntryDateEditable, isoDate, resolveInitialDate } from './entryForm';

const today = new Date(2026, 5, 23, 12);

describe('isoDate', () => {
  it('uses the device-local calendar day, not UTC', () => {
    // Local evening must stay on the local date even when UTC has already
    // rolled forward — otherwise the widget / openEntry fallback writes
    // tomorrow's entry while the homescreen still shows "no entry today".
    const localEvening = new Date(2026, 5, 23, 20, 30, 0);
    expect(isoDate(localEvening)).toBe('2026-06-23');
  });
});

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

  it('uses the same local date basis as isoDate', () => {
    const localEvening = new Date(2026, 5, 23, 20, 30, 0);

    expect(isEntryDateEditable(localEvening, '2026-06-23')).toBe(true);
    expect(isEntryDateEditable(localEvening, '2026-06-24')).toBe(false);
  });
});

describe('resolveInitialDate', () => {
  it('keeps an editable query date', () => {
    expect(resolveInitialDate(today, '2026-06-20')).toBe('2026-06-20');
  });

  it('falls back to today for a read-only historical date', () => {
    expect(resolveInitialDate(today, '2026-06-01')).toBe('2026-06-23');
  });

  it('falls back to the local calendar day when no query date is given', () => {
    const localEvening = new Date(2026, 5, 23, 20, 30, 0);
    expect(resolveInitialDate(localEvening, null)).toBe('2026-06-23');
  });
});
