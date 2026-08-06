import { render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import MetricTimeseries from './MetricTimeseries.svelte';

vi.mock('svelte-i18n', async () => {
  const { readable } = await import('svelte/store');

  return {
    _: readable((key: string) => key),
  };
});

const points = [
  {
    period_start: '2026-05-01',
    period_end: '2026-05-01',
    entry_count: 1,
    mood_avg: 3,
    energy_avg: 4,
    stress_avg: 2,
    sleep_quality_avg: null,
  },
  {
    period_start: '2026-05-02',
    period_end: '2026-05-02',
    entry_count: 1,
    mood_avg: 4,
    energy_avg: 5,
    stress_avg: 1,
    sleep_quality_avg: null,
  },
];

describe('MetricTimeseries', () => {
  it('renders axes, range-aware ticks and non-color metric styles', () => {
    const { container } = render(MetricTimeseries, {
      props: {
        points,
        range: 'year',
        loading: false,
        enabled: { mood_avg: true, energy_avg: true, stress_avg: true, sleep_quality_avg: false },
      },
    });

    expect(screen.getByText('trends.timeseries.score_axis')).toBeTruthy();
    expect(screen.getAllByText('2026-05').length).toBeGreaterThan(0);
    expect(container.querySelectorAll('.timeseries__line')).toHaveLength(3);
    expect(container.querySelector('[style*="8 5"]')).toBeTruthy();
    expect(container.querySelector('[style*="2 5"]')).toBeTruthy();
    expect(container.querySelectorAll('polygon.timeseries__point')).toHaveLength(4);
    expect(container.querySelectorAll('circle.timeseries__hit')).toHaveLength(6);
  });

  it('draws the sleep-quality line as a 4th square-marked series when enabled (#653 B2)', () => {
    const sleepPoints = points.map((p, i) => ({ ...p, sleep_quality_avg: i === 0 ? 3 : 5 }));
    const { container } = render(MetricTimeseries, {
      props: {
        points: sleepPoints,
        range: 'year',
        loading: false,
        enabled: { mood_avg: true, energy_avg: true, stress_avg: true, sleep_quality_avg: true },
      },
    });

    // Four metric lines now (mood/energy/stress/sleep) and the sleep line uses
    // its own dasharray + square markers so it stays separable without colour.
    expect(container.querySelectorAll('.timeseries__line')).toHaveLength(4);
    expect(container.querySelector('[style*="1 4"]')).toBeTruthy();
    // The sleep series contributes two square point markers.
    const squares = container.querySelectorAll('polygon.timeseries__point');
    expect(squares.length).toBeGreaterThan(4);
  });

  it('keeps the mood/energy/stress legend in sticky chrome with the Y-axis pattern', () => {
    const { container } = render(MetricTimeseries, {
      props: {
        points,
        range: 'week',
        loading: false,
        enabled: { mood_avg: true, energy_avg: true, stress_avg: true, sleep_quality_avg: false },
        axisDates: ['2026-05-01', '2026-05-02'],
      },
    });

    const legend = screen.getByLabelText('trends.timeseries.legend');
    expect(legend.textContent).toContain('trends.metric.mood');
    expect(legend.textContent).toContain('trends.metric.energy');
    expect(legend.textContent).toContain('trends.metric.stress');
    expect(legend.closest('.timeseries__head')).toBeTruthy();
    expect(container.querySelector('.timeseries__gutter')).toBeTruthy();
  });

  it('anchors the first/last date ticks away from the chart edges so labels stay unclipped (#631)', () => {
    const { container } = render(MetricTimeseries, {
      props: {
        points,
        range: 'week',
        loading: false,
        enabled: { mood_avg: true, energy_avg: true, stress_avg: true, sleep_quality_avg: false },
        axisDates: ['2026-05-01', '2026-05-02'],
      },
    });

    const ticks = container.querySelectorAll('.timeseries__tick--x');
    expect(ticks.length).toBe(2);
    expect(ticks[0]?.getAttribute('style')).toContain('text-anchor: start');
    expect(ticks[ticks.length - 1]?.getAttribute('style')).toContain('text-anchor: end');
  });

  it('renders skeleton and empty states', () => {
    const loading = render(MetricTimeseries, {
      props: {
        points: [],
        range: 'week',
        loading: true,
        enabled: { mood_avg: true, energy_avg: true, stress_avg: true, sleep_quality_avg: false },
      },
    });
    expect(loading.getByLabelText('trends.timeseries.loading')).toBeTruthy();
    loading.unmount();

    render(MetricTimeseries, {
      props: {
        points: [
          {
            period_start: '2026-05-01',
            period_end: '2026-05-01',
            entry_count: 0,
            mood_avg: null,
            energy_avg: null,
            stress_avg: null,
            sleep_quality_avg: null,
          },
        ],
        range: 'week',
        loading: false,
        enabled: { mood_avg: true, energy_avg: true, stress_avg: true, sleep_quality_avg: false },
      },
    });
    expect(screen.getByText('trends.timeseries.empty')).toBeTruthy();
    expect(screen.getByText('trends.empty_cta')).toBeTruthy();
  });
});
