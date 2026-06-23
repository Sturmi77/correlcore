import { render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import MobileTrendsSummary from './MobileTrendsSummary.svelte';

vi.mock('svelte-i18n', async () => {
  const { readable } = await import('svelte/store');
  return { _: readable((key: string) => key) };
});

const points = [
  {
    period_start: '2026-06-01',
    period_end: '2026-06-01',
    entry_count: 1,
    mood_avg: 3,
    energy_avg: 4,
    stress_avg: 4,
  },
  {
    period_start: '2026-06-02',
    period_end: '2026-06-02',
    entry_count: 1,
    mood_avg: 4,
    energy_avg: 3,
    stress_avg: 2,
  },
];

describe('MobileTrendsSummary', () => {
  it('renders a compact summary from the existing analytics responses', () => {
    render(MobileTrendsSummary, {
      props: {
        points,
        tagHeatmap: {
          start_date: '2026-06-01',
          end_date: '2026-06-02',
          tags: [
            {
              tag_id: 'focus',
              slug: 'focus',
              name: 'Focus',
              category: 'work',
              color: null,
              days: [{ date: '2026-06-01', count: 2 }],
            },
          ],
        },
        symptomHeatmap: {
          start_date: '2026-06-01',
          end_date: '2026-06-02',
          symptoms: [
            {
              symptom_id: 'fatigue',
              slug: 'fatigue',
              name: 'Fatigue',
              icon: null,
              days: [{ date: '2026-06-02', count: 1, max_intensity: 2 }],
            },
          ],
        },
      },
    });

    expect(screen.getByTestId('mobile-trends-summary')).toBeTruthy();
    expect(screen.getByText('trends.metric.stress')).toBeTruthy();
    expect(screen.getByText('Focus')).toBeTruthy();
    expect(screen.getByText('Fatigue')).toBeTruthy();
  });

  it('renders an explicit empty summary', () => {
    render(MobileTrendsSummary);
    expect(screen.getByTestId('mobile-trends-summary-empty')).toBeTruthy();
  });
});
