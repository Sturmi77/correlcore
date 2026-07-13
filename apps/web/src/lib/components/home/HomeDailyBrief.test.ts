import { render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import type { InsightMaturity } from '$lib/api/insights';
import HomeDailyBrief from './HomeDailyBrief.svelte';

vi.mock('svelte-i18n', () => ({
  _: {
    subscribe: (
      run: (
        formatter: (key: string, options?: { values?: Record<string, unknown> }) => string
      ) => void
    ) => {
      run((key: string, options?: { values?: Record<string, unknown> }) => {
        if (key === 'maturity.journey.compact_entries_until_next') {
          return `${options?.values?.remaining} more until next phase`;
        }
        if (options?.values) return `${key} ${JSON.stringify(options.values)}`;
        if (key.startsWith('maturity.')) return key;
        return key;
      });
      return () => undefined;
    },
  },
}));

const collectingMaturity: InsightMaturity = {
  phase: 'collecting',
  phase_index: 1,
  current_entries: 4,
  next_phase_at: 7,
  next_phase_label: 'early_patterns',
  entries_until_next: 3,
  user_message_key: 'maturity.collecting.description',
};

describe('HomeDailyBrief', () => {
  it('shows inline entries-until-milestone progress when maturity is present', () => {
    render(HomeDailyBrief, {
      props: {
        maturity: collectingMaturity,
        entries: [],
      },
    });

    expect(screen.getByTestId('home-brief-milestone-progress').textContent).toContain(
      '3 more until next phase'
    );
    expect(screen.getByRole('meter')).toBeTruthy();
  });

  it('enriches weekly bridge links with insight previews', () => {
    render(HomeDailyBrief, {
      props: {
        maturity: collectingMaturity,
        entries: [{ id: '1' } as never, { id: '2' } as never, { id: '3' } as never],
        latestInsight: {
          id: 'i1',
          subject_label: 'Energy',
          metric: 'energy',
          statement: 'Energy tracks with your walks.',
          confidence: 0.72,
        } as never,
      },
    });

    expect(screen.getByTestId('home-bridge-insights').textContent).toContain('Energy');
    expect(screen.getByTestId('home-bridge-trends').textContent).toContain('Energy');
  });

  it('shows the insight statement as primary text, subject label as caption', () => {
    render(HomeDailyBrief, {
      props: {
        maturity: collectingMaturity,
        entries: [],
        latestInsight: {
          id: 'i1',
          subject_label: 'Energy',
          metric: 'energy',
          statement: 'Energy tracks with your walks.',
          confidence: 0.72,
        } as never,
      },
    });

    expect(screen.getByTestId('daily-brief-lead-statement').textContent).toContain(
      'Energy tracks with your walks.'
    );
    expect(screen.getByTestId('daily-brief-lead-caption').textContent).toContain('Energy');
  });

  it('renders work context summary rows when dashboard data is present', () => {
    render(HomeDailyBrief, {
      props: {
        workContextSummary: [
          {
            work_context: 'office',
            entry_count: 8,
            mood_avg: 3.75,
            energy_avg: 3.4,
            stress_avg: 2.8,
          },
          {
            work_context: 'homeoffice',
            entry_count: 5,
            mood_avg: 4.1,
            energy_avg: 3.8,
            stress_avg: 2.1,
          },
        ],
      },
    });

    expect(screen.getByText('home.brief.work_context_heading')).toBeTruthy();
    expect(screen.getByText('entry.work_context.office')).toBeTruthy();
    expect(screen.getByText('entry.work_context.homeoffice')).toBeTruthy();
    expect(screen.getByText(/"mood":"4\.1"/)).toBeTruthy();
    expect(screen.getByText(/"count":5/)).toBeTruthy();
  });

  it('switches work context rows to energy averages', async () => {
    const { fireEvent } = await import('@testing-library/svelte');
    render(HomeDailyBrief, {
      props: {
        workContextSummary: [
          {
            work_context: 'office',
            entry_count: 8,
            mood_avg: 3.75,
            energy_avg: 3.4,
            stress_avg: 2.8,
          },
          {
            work_context: 'homeoffice',
            entry_count: 5,
            mood_avg: 4.1,
            energy_avg: 3.8,
            stress_avg: 2.1,
          },
        ],
      },
    });

    await fireEvent.click(screen.getByTestId('home-work-context-metric-energy'));
    expect(screen.getByText(/"mood":"3\.8"/)).toBeTruthy();
  });

  it('assigns inverted stress highlights (lowest stress = high, highest = low)', async () => {
    const { fireEvent } = await import('@testing-library/svelte');
    render(HomeDailyBrief, {
      props: {
        workContextSummary: [
          {
            work_context: 'office',
            entry_count: 9,
            mood_avg: 3.4,
            energy_avg: 3.2,
            stress_avg: 3.6,
          },
          {
            work_context: 'homeoffice',
            entry_count: 8,
            mood_avg: 3.9,
            energy_avg: 3.7,
            stress_avg: 2.8,
          },
          {
            work_context: 'weekend',
            entry_count: 4,
            mood_avg: 4.2,
            energy_avg: 3.8,
            stress_avg: 2.2,
          },
        ],
      },
    });

    await fireEvent.click(screen.getByTestId('home-work-context-metric-stress'));

    const rows = [...document.querySelectorAll('.daily-brief__work-context-row')];
    const byContext = Object.fromEntries(
      rows.map((row) => [
        row.querySelector('span')?.textContent ?? '',
        row.getAttribute('data-highlight'),
      ])
    );

    expect(byContext['entry.work_context.weekend']).toBe('high');
    expect(byContext['entry.work_context.office']).toBe('low');
    expect(byContext['entry.work_context.homeoffice']).toBe('none');
  });
});
