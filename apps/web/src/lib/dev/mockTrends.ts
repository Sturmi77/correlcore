import type { EntryStreakResponse, TagHeatmapResponse, TimeseriesResponse } from '$lib/api/stats';
import { localIsoDate, shiftIsoDate } from '$lib/utils/streak';

const today = localIsoDate(new Date());
const start = shiftIsoDate(today, -13);

export const mockTimeseries: TimeseriesResponse = {
  range: 'week',
  points: Array.from({ length: 14 }, (_, idx) => {
    const date = shiftIsoDate(start, idx);
    return {
      period_start: date,
      period_end: date,
      entry_count: 1,
      mood_avg: 3 + ((idx + 1) % 3),
      energy_avg: 2 + (idx % 4),
      stress_avg: 2 + ((idx + 2) % 3),
    };
  }),
};

export const mockTagHeatmap: TagHeatmapResponse = {
  start_date: start,
  end_date: today,
  tags: [
    {
      tag_id: 'mock-tag-focus',
      slug: 'focus',
      name: 'Focus work',
      category: 'work',
      color: null,
      days: [
        { date: shiftIsoDate(today, -5), count: 1 },
        { date: shiftIsoDate(today, -2), count: 2 },
        { date: today, count: 1 },
      ],
    },
    {
      tag_id: 'mock-tag-walk',
      slug: 'walk',
      name: 'Walk',
      category: 'sport',
      color: null,
      days: [
        { date: shiftIsoDate(today, -4), count: 1 },
        { date: shiftIsoDate(today, -1), count: 1 },
      ],
    },
  ],
};

export const mockEntryStreak: EntryStreakResponse = {
  current_streak: 6,
  longest_streak: 9,
  total_entry_days: 42,
  last_entry_date: today,
  as_of: today,
};
