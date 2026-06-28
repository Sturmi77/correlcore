import { describe, expect, it } from 'vitest';
import type { EntryResponse } from '$lib/api/entries';
import type { SymptomHeatmapSymptom } from '$lib/api/stats';
import {
  buildMoodByDate,
  buildSymptomCalendarGrid,
  buildSymptomTrendSeries,
  rankEligibleSymptoms,
  symptomOccurrenceCount,
} from './symptomAnalyticsViews';

function symptomWithDays(slug: string, dates: string[], id = `id-${slug}`): SymptomHeatmapSymptom {
  return {
    symptom_id: id,
    slug,
    name: slug,
    icon: null,
    days: dates.map((date) => ({ date, count: 1, max_intensity: 1 })),
  };
}

function entry(date: string, moodScore: number): EntryResponse {
  return {
    id: `entry-${date}`,
    user_id: 'user-1',
    entry_date: date,
    slot: 'day',
    mood_score: moodScore,
    energy: 3,
    stress: 3,
    cycle_day: null,
    work_context: 'homeoffice',
    source: 'direct',
    note: null,
    created_at: '',
    updated_at: '',
  };
}

describe('symptomAnalyticsViews', () => {
  it('filters symptoms below the minimum occurrence threshold', () => {
    const symptoms = [
      symptomWithDays('rare', ['2026-01-01', '2026-01-02']),
      symptomWithDays(
        'common',
        Array.from({ length: 5 }, (_, i) => `2026-01-${String(i + 3).padStart(2, '0')}`)
      ),
    ];
    const eligible = rankEligibleSymptoms(symptoms);
    expect(eligible).toHaveLength(1);
    expect(eligible[0].slug).toBe('common');
    expect(symptomOccurrenceCount(eligible[0])).toBe(5);
  });

  it('builds a Monday-aligned calendar grid with leading padding', () => {
    const presence = new Map([
      ['2026-01-01', true],
      ['2026-01-03', true],
    ]);
    const cells = buildSymptomCalendarGrid('2026-01-01', '2026-01-07', presence);
    expect(cells[0].date).toBeNull();
    expect(cells[1].date).toBeNull();
    expect(cells[2].date).toBeNull();
    expect(cells[3].date).toBe('2026-01-01');
    expect(cells[3].present).toBe(true);
    const datedCells = cells.filter((cell) => cell.date);
    expect(datedCells[datedCells.length - 1].date).toBe('2026-01-07');
    expect(cells.length % 7).toBe(0);
  });

  it('builds rolling symptom frequency and mood averages', () => {
    const dates = ['2026-01-01', '2026-01-02', '2026-01-03', '2026-01-04'];
    const presence = new Map([
      ['2026-01-01', true],
      ['2026-01-02', true],
      ['2026-01-03', false],
      ['2026-01-04', true],
    ]);
    const mood = buildMoodByDate([entry('2026-01-01', 2), entry('2026-01-02', 4)]);

    const series = buildSymptomTrendSeries(dates, presence, mood, 2);
    expect(series[3].symptomFrequency).toBe(0.5);
    expect(series[1].moodAverage).toBe(3);
  });
});
