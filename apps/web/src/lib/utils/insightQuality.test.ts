import { describe, expect, it } from 'vitest';
import { dayEntryDatesFromIsoEntries, estimateInsightReadiness } from './insightQuality';

function dates(count: number, startDay = 1): string[] {
  return Array.from({ length: count }, (_, idx) => {
    const date = new Date(Date.UTC(2026, 4, startDay + idx));
    return date.toISOString().slice(0, 10);
  });
}

describe('estimateInsightReadiness', () => {
  it('uses neutral copy stage without an estimate for 0-3 entries', () => {
    const estimate = estimateInsightReadiness({
      dayEntryDates: dates(3),
      asOfIso: '2026-05-16',
    });

    expect(estimate.stage).toBe('getting_started');
    expect(estimate.estimatedWeeks).toBeNull();
    expect(estimate.showProgressFraction).toBe(false);
  });

  it('estimates weeks from the last 14 days for 4-29 entries', () => {
    const estimate = estimateInsightReadiness({
      dayEntryDates: dates(10, 1),
      asOfIso: '2026-05-14',
    });

    expect(estimate.stage).toBe('building_with_pace');
    expect(estimate.recentEntryCount).toBe(10);
    expect(estimate.entriesRemaining).toBe(20);
    expect(estimate.estimatedWeeks).toBe(4);
    expect(estimate.showProgressFraction).toBe(true);
  });

  it('omits the estimate when 4-29 entries have no recent data', () => {
    const estimate = estimateInsightReadiness({
      dayEntryDates: dates(8, 1),
      asOfIso: '2026-06-01',
    });

    expect(estimate.stage).toBe('building_no_recent');
    expect(estimate.recentEntryCount).toBe(0);
    expect(estimate.estimatedWeeks).toBeNull();
  });

  it('marks the first insight stage from 30 entries', () => {
    const estimate = estimateInsightReadiness({
      dayEntryDates: dates(30, 1),
      asOfIso: '2026-05-30',
    });

    expect(estimate.stage).toBe('ready_low');
    expect(estimate.progressRatio).toBe(1);
    expect(estimate.showProgressFraction).toBe(false);
  });

  it('marks full insights from 90 entries', () => {
    const estimate = estimateInsightReadiness({
      dayEntryDates: dates(90),
      asOfIso: '2026-07-29',
    });

    expect(estimate.stage).toBe('ready_full');
  });
});

describe('dayEntryDatesFromIsoEntries', () => {
  it('deduplicates day entries and ignores non-day slots', () => {
    const result = dayEntryDatesFromIsoEntries([
      { entry_date: '2026-05-01', slot: 'day' },
      { entry_date: '2026-05-01', slot: 'evening' },
      { entry_date: '2026-05-02', slot: 'day' },
      { entry_date: '2026-05-02', slot: 'day' },
    ]);

    expect(result).toEqual(['2026-05-01', '2026-05-02']);
  });
});
