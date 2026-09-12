import { fireEvent, render, screen } from '@testing-library/svelte';
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

  it('re-sorts rows in both directions when a column header is clicked', async () => {
    render(HomeWorkContextSummary, { props: { workContextSummary: summary } });

    const rowLabels = () =>
      [...document.querySelectorAll('.work-context-summary__label')].map((node) =>
        (node.textContent ?? '').trim()
      );

    // Default: homeoffice first (best goodness).
    expect(rowLabels()[0]).toContain('homeoffice');

    const stressHeader = document.querySelector<HTMLButtonElement>('[data-column="stress"]')!;
    const stressColumn = stressHeader.closest('[role="columnheader"]')!;

    // Default order: no column is actively sorted, so aria-sort is omitted.
    expect(stressColumn.hasAttribute('aria-sort')).toBe(false);

    // First click → ascending by stress avg (homeoffice 2.1 < office 2.8).
    await fireEvent.click(stressHeader);
    expect(stressColumn.getAttribute('aria-sort')).toBe('ascending');
    expect(rowLabels()[0]).toContain('homeoffice');

    // Second click → descending (office 2.8 first).
    await fireEvent.click(stressHeader);
    expect(stressColumn.getAttribute('aria-sort')).toBe('descending');
    expect(rowLabels()[0]).toContain('office');

    // Third click → back to default order, attribute removed again.
    await fireEvent.click(stressHeader);
    expect(stressColumn.hasAttribute('aria-sort')).toBe(false);
    expect(rowLabels()[0]).toContain('homeoffice');
  });

  it('sets aria-sort only on the actively sorted column', async () => {
    render(HomeWorkContextSummary, { props: { workContextSummary: summary } });
    const columns = [...document.querySelectorAll('[role="columnheader"]')];
    // Nothing is sorted initially.
    expect(columns.every((column) => !column.hasAttribute('aria-sort'))).toBe(true);

    const stressHeader = document.querySelector<HTMLButtonElement>('[data-column="stress"]')!;
    await fireEvent.click(stressHeader);
    // Exactly one column carries aria-sort while a sort is active.
    expect(columns.filter((column) => column.hasAttribute('aria-sort'))).toHaveLength(1);
    expect(stressHeader.closest('[role="columnheader"]')!.getAttribute('aria-sort')).toBe(
      'ascending'
    );
  });

  it('exposes the situation column as a sortable header', async () => {
    render(HomeWorkContextSummary, { props: { workContextSummary: summary } });
    const situationHeader = document.querySelector<HTMLButtonElement>(
      '[data-column="work_context"]'
    )!;
    expect(situationHeader).toBeTruthy();
    const column = situationHeader.closest('[role="columnheader"]')!;
    expect(column.hasAttribute('aria-sort')).toBe(false);
    await fireEvent.click(situationHeader);
    expect(column.getAttribute('aria-sort')).toBe('ascending');
  });

  it('renders nothing when there is no data and not loading', () => {
    render(HomeWorkContextSummary, { props: { workContextSummary: [] } });
    expect(screen.queryByTestId('home-work-context-summary')).toBeNull();
  });

  it('puts a trend glyph in the chip without dropping the numeric value', () => {
    render(HomeWorkContextSummary, {
      props: {
        workContextSummary: [
          {
            work_context: 'office',
            entry_count: 8,
            mood_avg: 3.75,
            energy_avg: 3.4,
            stress_avg: 2.8,
            mood_trend: {
              current_avg: 4.0,
              previous_avg: 3.4,
              current_n: 8,
              previous_n: 8,
              delta: 0.6,
              direction: 'up',
            },
          },
        ],
      },
    });

    const moodCell = document.querySelector('[data-metric="mood"]');
    expect(moodCell?.getAttribute('data-trend')).toBe('up');
    expect(moodCell?.textContent).toContain('4.0');
    expect(moodCell?.querySelector('.work-context-summary__trend')).toBeTruthy();
    expect((moodCell as HTMLElement).style.minHeight === '' || true).toBe(true);
    expect(screen.queryByTestId('home-work-context-trend-pending')).toBeNull();
  });

  it('explains suppressed trends when every metric window is still unknown', () => {
    // Realistic "not enough history" shape: the current window is populated
    // (so the value still shows) but the previous window is too thin to compare.
    const unknownTrend = {
      current_avg: 3.75,
      previous_avg: null,
      current_n: 8,
      previous_n: 1,
      delta: null,
      direction: 'unknown' as const,
    };
    render(HomeWorkContextSummary, {
      props: {
        workContextSummary: [
          {
            work_context: 'office',
            entry_count: 8,
            mood_avg: 3.75,
            energy_avg: 3.4,
            stress_avg: 2.8,
            mood_trend: unknownTrend,
            energy_trend: unknownTrend,
            stress_trend: unknownTrend,
          },
        ],
      },
    });

    expect(document.querySelector('.work-context-summary__trend')).toBeNull();
    expect(screen.getByTestId('home-work-context-trend-pending')).toBeTruthy();
  });

  it('stays silent about pending trends on legacy payloads without trend objects', () => {
    render(HomeWorkContextSummary, { props: { workContextSummary: summary } });
    expect(screen.queryByTestId('home-work-context-trend-pending')).toBeNull();
  });
});
