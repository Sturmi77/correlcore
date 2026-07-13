import { describe, expect, it } from 'vitest';
import { dayEntryDatesFromIsoEntries } from './insightQuality';

describe('dayEntryDatesFromIsoEntries', () => {
  it('returns sorted unique day-slot dates', () => {
    expect(
      dayEntryDatesFromIsoEntries([
        { entry_date: '2026-05-10', slot: 'day' },
        { entry_date: '2026-05-12', slot: 'day' },
        { entry_date: '2026-05-10', slot: 'morning' },
        { entry_date: '2026-05-11', slot: 'day' },
      ])
    ).toEqual(['2026-05-10', '2026-05-11', '2026-05-12']);
  });
});
