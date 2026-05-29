import type { HabitStatsResponse } from '$lib/api/habits';
import type {
  EntryStreakResponse,
  SymptomHeatmapResponse,
  TagHeatmapResponse,
  TimeseriesResponse,
} from '$lib/api/stats';
import type { TagResponse } from '$lib/api/tags';
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

export const mockSymptomHeatmap: SymptomHeatmapResponse = {
  start_date: start,
  end_date: today,
  symptoms: [
    {
      symptom_id: 'mock-symptom-fatigue',
      slug: 'fatigue',
      name: 'Fatigue',
      icon: 'battery-low',
      days: [
        { date: shiftIsoDate(today, -6), count: 1, max_intensity: 1 },
        { date: shiftIsoDate(today, -3), count: 1, max_intensity: 2 },
        { date: today, count: 1, max_intensity: 1 },
      ],
    },
    {
      symptom_id: 'mock-symptom-headache',
      slug: 'headache',
      name: 'Headache',
      icon: 'activity',
      days: [
        { date: shiftIsoDate(today, -4), count: 1, max_intensity: 3 },
        { date: shiftIsoDate(today, -2), count: 1, max_intensity: 1 },
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

export const mockHabitTags: TagResponse[] = [
  {
    id: 'mock-tag-walk',
    user_id: 'mock-user',
    slug: 'walk',
    name: 'Walk',
    category: 'sport',
    icon: 'footprints',
    color: null,
    is_default: false,
    is_hidden: false,
    habit_type: 'build',
    target_frequency: 4,
    created_at: `${today}T00:00:00Z`,
    updated_at: `${today}T00:00:00Z`,
  },
  {
    id: 'mock-tag-focus',
    user_id: 'mock-user',
    slug: 'focus',
    name: 'Focus work',
    category: 'work',
    icon: 'briefcase',
    color: null,
    is_default: false,
    is_hidden: false,
    habit_type: 'reduce',
    target_frequency: 5,
    created_at: `${today}T00:00:00Z`,
    updated_at: `${today}T00:00:00Z`,
  },
];

export const mockHabits: HabitStatsResponse[] = [
  {
    tag_id: 'mock-tag-walk',
    habit_type: 'build',
    target_frequency: 4,
    window: 28,
    start_date: shiftIsoDate(today, -27),
    end_date: today,
    days_tracked: 12,
    days_total: 28,
    target_days: 16,
    adherence_rate: 75,
    correlation_score: 0.48,
  },
  {
    tag_id: 'mock-tag-focus',
    habit_type: 'reduce',
    target_frequency: 5,
    window: 28,
    start_date: shiftIsoDate(today, -27),
    end_date: today,
    days_tracked: 14,
    days_total: 28,
    target_days: 20,
    adherence_rate: 100,
    correlation_score: null,
  },
];

export const mockTagCooccurrence = {
  range: '90d' as const,
  start_date: shiftIsoDate(today, -89),
  end_date: today,
  min_count: 2,
  pairs: [
    {
      tag_a: {
        tag_id: 'mock-tag-focus',
        slug: 'focus',
        name: 'Focus work',
        category: 'work',
        color: null,
      },
      tag_b: {
        tag_id: 'mock-tag-walk',
        slug: 'walk',
        name: 'Walk',
        category: 'sport',
        color: null,
      },
      count: 5,
      pct_of_a: 71.4,
      pct_of_b: 83.3,
    },
    {
      tag_a: {
        tag_id: 'mock-tag-focus',
        slug: 'focus',
        name: 'Focus work',
        category: 'work',
        color: null,
      },
      tag_b: {
        tag_id: 'mock-tag-coffee',
        slug: 'coffee',
        name: 'Coffee',
        category: 'consumption',
        color: null,
      },
      count: 4,
      pct_of_a: 57.1,
      pct_of_b: 80.0,
    },
    {
      tag_a: {
        tag_id: 'mock-tag-walk',
        slug: 'walk',
        name: 'Walk',
        category: 'sport',
        color: null,
      },
      tag_b: {
        tag_id: 'mock-tag-coffee',
        slug: 'coffee',
        name: 'Coffee',
        category: 'consumption',
        color: null,
      },
      count: 3,
      pct_of_a: 50.0,
      pct_of_b: 60.0,
    },
    {
      tag_a: {
        tag_id: 'mock-tag-read',
        slug: 'read',
        name: 'Read',
        category: 'leisure',
        color: null,
      },
      tag_b: {
        tag_id: 'mock-tag-walk',
        slug: 'walk',
        name: 'Walk',
        category: 'sport',
        color: null,
      },
      count: 2,
      pct_of_a: 66.7,
      pct_of_b: 33.3,
    },
    {
      tag_a: {
        tag_id: 'mock-tag-read',
        slug: 'read',
        name: 'Read',
        category: 'leisure',
        color: null,
      },
      tag_b: {
        tag_id: 'mock-tag-coffee',
        slug: 'coffee',
        name: 'Coffee',
        category: 'consumption',
        color: null,
      },
      count: 2,
      pct_of_a: 66.7,
      pct_of_b: 40.0,
    },
  ],
};
