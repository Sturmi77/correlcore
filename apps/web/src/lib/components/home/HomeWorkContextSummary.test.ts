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
  const summary = [
    {
      work_context: 'office' as const,
      entry_count: 8,
      mood_avg: 3.75,
      energy_avg: 3.4,
      stress_avg: 2.8,
    },
    {
      work_context: 'homeoffice' as const,
      entry_count: 5,
      mood_avg: 4.1,
      energy_avg: 3.8,
      stress_avg: 2.1,
    },
  ];

  it('renders a heatmap cell for every metric of every context', () => {
    render(HomeWorkContextSummary, { props: { workContextSummary: summary } });

    expect(screen.getByText('home.brief.work_context_heading')).toBeTruthy();
    expect(screen.getByText('entry.work_context.office')).toBeTruthy();
    expect(screen.getByText('entry.work_context.homeoffice')).toBeTruthy();

    // One row header + 3 metric cells per context are present at once
    // (mood/energy/stress shown together, no metric switcher).
    const cells = document.querySelectorAll('.work-context-summary__cell');
    expect(cells.length).toBe(summary.length * 3);
    // Unique averages: homeoffice mood 4.1 and stress 2.1.
    expect(screen.getByText('4.1')).toBeTruthy();
    expect(screen.getByText('2.1')).toBeTruthy();
  });

  it('orders rows best-situation-first by mean goodness', () => {
    render(HomeWorkContextSummary, { props: { workContextSummary: summary } });

    const labels = [...document.querySelectorAll('.work-context-summary__label')].map((node) =>
      (node.textContent ?? '').trim()
    );
    // homeoffice has higher mood/energy and lower stress → higher goodness.
    expect(labels[0]).toContain('entry.work_context.homeoffice');
    expect(labels[1]).toContain('entry.work_context.office');
  });

  it('inverts stress so the lowest-stress context gets the strongest cell level', () => {
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
            work_context: 'vacation',
            entry_count: 4,
            mood_avg: 4.2,
            energy_avg: 3.8,
            stress_avg: 2.2,
          },
        ],
      },
    });

    const stressLevelByContext = Object.fromEntries(
      [...document.querySelectorAll('.work-context-summary__row')].map((row) => {
        const label = row.querySelector('.work-context-summary__label')?.textContent ?? '';
        const stressCell = row.querySelector('[data-metric="stress"]');
        return [label.trim(), Number(stressCell?.getAttribute('data-level'))];
      })
    );

    const vacation = Object.entries(stressLevelByContext).find(([label]) =>
      label.includes('vacation')
    )?.[1];
    const office = Object.entries(stressLevelByContext).find(([label]) =>
      label.includes('office')
    )?.[1];
    // vacation stress 2.2 -> goodness 3.8; office stress 3.6 -> goodness 2.4.
    expect(vacation).toBeGreaterThan(office as number);
  });

  it('renders nothing when there is no data and not loading', () => {
    render(HomeWorkContextSummary, { props: { workContextSummary: [] } });
    expect(screen.queryByTestId('home-work-context-summary')).toBeNull();
  });
});
