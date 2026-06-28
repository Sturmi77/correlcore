import type { EntryResponse } from '$lib/api/entries';
import type { SymptomHeatmapSymptom } from '$lib/api/stats';
import { buildIsoDateRange } from '$lib/utils/charts';

export const SYMPTOM_VIEW_MIN_OCCURRENCES = 5;
export const SYMPTOM_CALENDAR_MAX_VISIBLE = 8;
export const SYMPTOM_TREND_MAX_VISIBLE = 4;
export const SYMPTOM_TREND_DEFAULT_DAYS = 60;
export const SYMPTOM_TREND_ROLLING_WINDOW = 7;

export interface SymptomCalendarCell {
  date: string | null;
  present: boolean;
}

export interface SymptomTrendPoint {
  date: string;
  symptomFrequency: number;
  moodAverage: number | null;
  moodUncertainty: number | null;
}

export function symptomOccurrenceCount(symptom: SymptomHeatmapSymptom): number {
  return symptom.days.reduce((sum, day) => sum + (day.count > 0 ? 1 : 0), 0);
}

export function rankEligibleSymptoms(
  symptoms: SymptomHeatmapSymptom[],
  minOccurrences = SYMPTOM_VIEW_MIN_OCCURRENCES
): SymptomHeatmapSymptom[] {
  return [...symptoms]
    .filter((symptom) => symptomOccurrenceCount(symptom) >= minOccurrences)
    .sort((a, b) => symptomOccurrenceCount(b) - symptomOccurrenceCount(a));
}

export function symptomPresenceByDate(symptom: SymptomHeatmapSymptom): Map<string, boolean> {
  const map = new Map<string, boolean>();
  for (const day of symptom.days) {
    if (day.count > 0) map.set(day.date, true);
  }
  return map;
}

/** Monday-aligned contribution grid (GitHub-style rows = weekdays). */
export function buildSymptomCalendarGrid(
  startDate: string,
  endDate: string,
  presenceByDate: Map<string, boolean>
): SymptomCalendarCell[] {
  const dates = buildIsoDateRange(startDate, endDate);
  if (dates.length === 0) return [];

  const firstWeekday = weekdayMondayIndex(dates[0]);
  const cells: SymptomCalendarCell[] = Array.from({ length: firstWeekday }, () => ({
    date: null,
    present: false,
  }));

  for (const date of dates) {
    cells.push({
      date,
      present: presenceByDate.get(date) ?? false,
    });
  }

  const remainder = cells.length % 7;
  if (remainder !== 0) {
    const pad = 7 - remainder;
    for (let i = 0; i < pad; i += 1) {
      cells.push({ date: null, present: false });
    }
  }

  return cells;
}

export function buildMoodByDate(entries: readonly EntryResponse[]): Map<string, number> {
  const map = new Map<string, number>();
  for (const entry of entries) {
    if (entry.slot === 'day') {
      map.set(entry.entry_date, entry.mood_score);
    }
  }
  return map;
}

export function buildSymptomTrendSeries(
  dates: string[],
  presenceByDate: Map<string, boolean>,
  moodByDate: Map<string, number>,
  rollingWindowDays = SYMPTOM_TREND_ROLLING_WINDOW
): SymptomTrendPoint[] {
  return dates.map((date, index) => {
    const windowDates = dates.slice(Math.max(0, index - rollingWindowDays + 1), index + 1);
    const symptomHits = windowDates.filter((d) => presenceByDate.get(d)).length;
    const symptomFrequency = symptomHits / windowDates.length;

    const moodValues = windowDates
      .map((d) => moodByDate.get(d))
      .filter((value): value is number => value !== undefined);
    const moodAverage =
      moodValues.length > 0
        ? moodValues.reduce((sum, value) => sum + value, 0) / moodValues.length
        : null;
    const moodUncertainty =
      moodValues.length > 1 ? standardError(moodValues) : moodValues.length === 1 ? 0 : null;

    return {
      date,
      symptomFrequency,
      moodAverage,
      moodUncertainty,
    };
  });
}

export function trendDatesForHeatmap(
  startDate: string,
  endDate: string,
  lastDays = SYMPTOM_TREND_DEFAULT_DAYS
): string[] {
  const full = buildIsoDateRange(startDate, endDate);
  if (full.length <= lastDays) return full;
  return full.slice(full.length - lastDays);
}

function weekdayMondayIndex(isoDate: string): number {
  const day = new Date(`${isoDate}T12:00:00`).getDay();
  return (day + 6) % 7;
}

function standardError(values: number[]): number {
  const mean = values.reduce((sum, value) => sum + value, 0) / values.length;
  const variance =
    values.reduce((sum, value) => sum + (value - mean) ** 2, 0) / (values.length - 1);
  return Math.sqrt(variance / values.length);
}
