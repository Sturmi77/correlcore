import { fireEvent, render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import type { EntryResponse } from '$lib/api/entries';
import SymptomAnalyticsSection from './SymptomAnalyticsSection.svelte';
vi.mock('svelte-i18n', async () => {
  const { readable } = await import('svelte/store');
  return {
    _: readable((key: string, options?: { values?: Record<string, unknown> }) => {
      if (options?.values) return `${key}:${JSON.stringify(options.values)}`;
      return key;
    }),
  };
});

const heatmap = {
  start_date: '2026-01-01',
  end_date: '2026-01-14',
  symptoms: [
    {
      symptom_id: 'sym-1',
      slug: 'headache',
      name: 'Headache',
      icon: null,
      days: Array.from({ length: 6 }, (_, index) => ({
        date: `2026-01-${String(index + 1).padStart(2, '0')}`,
        count: 1,
        max_intensity: 1,
      })),
    },
  ],
};

function moodEntry(date: string, moodScore: number): EntryResponse {
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

describe('SymptomAnalyticsSection', () => {
  it('renders calendar and trend sections for eligible symptoms', () => {
    render(SymptomAnalyticsSection, {
      props: {
        heatmap,
        entries: heatmap.symptoms[0].days.map((day) => moodEntry(day.date, 3)),
        phase: 'early_patterns',
      },
    });

    expect(screen.getByText('insights.symptoms.calendar_heading')).toBeTruthy();
    expect(screen.getByText('insights.symptoms.trend_heading')).toBeTruthy();
    expect(screen.queryByText('insights.symptoms.cooccurrence_heading')).toBeNull();
    expect(
      screen.getAllByRole('heading', { name: 'Headache', level: 3 }).length
    ).toBeGreaterThanOrEqual(2);
    expect(screen.getByLabelText('insights.symptoms.calendar_legend')).toBeTruthy();
  });

  it('shows symptom co-occurrence from provisional phase when data exists', () => {
    render(SymptomAnalyticsSection, {
      props: {
        heatmap,
        entries: [],
        phase: 'provisional',
        cooccurrence: {
          range: '90d',
          start_date: '2026-01-01',
          end_date: '2026-01-14',
          min_count: 2,
          cells: [
            {
              symptom: { symptom_id: 'sym-1', slug: 'headache', name: 'Headache', icon: null },
              tag: {
                tag_id: 'tag-1',
                slug: 'focus',
                name: 'Focus',
                category: 'work',
                color: null,
              },
              phi: 0.2,
              co_count: 3,
              jaccard: 0.4,
              lift: 1.2,
              symptom_count: 4,
              tag_count: 5,
              total_count: 10,
              p_value_corrected: 0.1,
              confounder: null,
            },
          ],
        },
      },
    });

    expect(screen.getByText('insights.symptoms.cooccurrence_heading')).toBeTruthy();
  });

  it('dispatches selectDate from calendar cells', async () => {
    const handler = vi.fn();
    const { container } = render(SymptomAnalyticsSection, {
      props: {
        heatmap,
        entries: [],
        phase: 'early_patterns',
      },
      events: { selectDate: handler },
    });

    const button = container.querySelector(
      '.symptom-calendar__cell:not(.symptom-calendar__cell--pad)'
    ) as HTMLElement;
    await fireEvent.click(button);
    expect(handler).toHaveBeenCalledOnce();
  });
});
