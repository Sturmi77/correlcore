import { render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import HomeWorkContextSummary from './HomeWorkContextSummary.svelte';

vi.mock('svelte-i18n', () => ({
  _: {
    subscribe: (
      run: (
        formatter: (key: string, options?: { values?: Record<string, unknown> }) => string
      ) => void
    ) => {
      run((key: string, options?: { values?: Record<string, unknown> }) => {
        if (options?.values) return `${key} ${JSON.stringify(options.values)}`;
        return key;
      });
      return () => undefined;
    },
  },
}));

describe('HomeWorkContextSummary', () => {
  it('renders work context summary rows when dashboard data is present', () => {
    render(HomeWorkContextSummary, {
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
    render(HomeWorkContextSummary, {
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
    render(HomeWorkContextSummary, {
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
            work_context: 'vacation',
            entry_count: 4,
            mood_avg: 4.2,
            energy_avg: 3.8,
            stress_avg: 2.2,
          },
        ],
      },
    });

    await fireEvent.click(screen.getByTestId('home-work-context-metric-stress'));

    const rows = [...document.querySelectorAll('.work-context-summary__row')];
    const byContext = Object.fromEntries(
      rows.map((row) => [
        row.querySelector('span')?.textContent ?? '',
        row.getAttribute('data-highlight'),
      ])
    );

    expect(byContext['entry.work_context.vacation']).toBe('high');
    expect(byContext['entry.work_context.office']).toBe('low');
    expect(byContext['entry.work_context.homeoffice']).toBe('none');
  });
});
