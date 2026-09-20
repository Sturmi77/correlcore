import { fireEvent, render } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import UnifiedStripChart from './UnifiedStripChart.svelte';
import { buildAxisBuckets } from '$lib/utils/compareAxisZoom';

vi.mock('svelte-i18n', async () => {
  const { readable } = await import('svelte/store');

  return {
    _: readable((key: string) => key),
  };
});

const enabled = {
  mood_avg: true,
  energy_avg: true,
  stress_avg: true,
  sleep_quality_avg: false,
  sleep_minutes_avg: false,
};

describe('UnifiedStripChart', () => {
  it('encodes stress after display inversion so high raw stress is negative', () => {
    const { container } = render(UnifiedStripChart, {
      props: {
        axisDates: ['2026-05-01', '2026-05-02'],
        enabled,
        points: [
          {
            period_start: '2026-05-01',
            period_end: '2026-05-01',
            entry_count: 1,
            mood_avg: 3,
            energy_avg: 3,
            stress_avg: 5,
            sleep_quality_avg: null,
          },
          {
            period_start: '2026-05-02',
            period_end: '2026-05-02',
            entry_count: 1,
            mood_avg: 3,
            energy_avg: 3,
            stress_avg: 1,
            sleep_quality_avg: null,
          },
        ],
      },
    });

    const stressCells = container.querySelectorAll('[data-metric="stress_avg"] .strip__cell');

    expect(stressCells).toHaveLength(2);
    expect(stressCells[0]?.getAttribute('data-sign')).toBe('neg');
    expect(stressCells[1]?.getAttribute('data-sign')).toBe('pos');
  });

  it('renders one cell per bucket and encodes the mean of logged days (#482 Option A)', () => {
    const axisDates = ['2026-05-01', '2026-05-02', '2026-05-03'];
    const buckets = buildAxisBuckets(axisDates, 1); // stage 1 = 3-day → single bucket
    expect(buckets).toHaveLength(1);

    const { container } = render(UnifiedStripChart, {
      props: {
        axisDates,
        buckets,
        enabled,
        points: [
          {
            period_start: '2026-05-01',
            period_end: '2026-05-01',
            entry_count: 1,
            mood_avg: 4,
            energy_avg: 3,
            stress_avg: 3,
            sleep_quality_avg: null,
          },
          {
            period_start: '2026-05-02',
            period_end: '2026-05-02',
            entry_count: 1,
            mood_avg: 4,
            energy_avg: 3,
            stress_avg: 3,
            sleep_quality_avg: null,
          },
          // 2026-05-03 missing — mean must ignore it, not treat as 0.
        ],
      },
    });

    const moodCells = container.querySelectorAll('[data-metric="mood_avg"] .strip__cell');
    // One column per bucket, not per day.
    expect(moodCells).toHaveLength(1);
    // Mean of logged mood (4, 4) = 4 > midpoint 3 → positive.
    expect(moodCells[0]?.getAttribute('data-sign')).toBe('pos');
    expect(Number(moodCells[0]?.getAttribute('opacity'))).toBeGreaterThan(0);
  });

  it('fades partial edge buckets and leaves empty buckets transparent', () => {
    const axisDates = ['2026-05-01', '2026-05-02', '2026-05-03', '2026-05-04'];
    // stage 1 = 3-day chunks from the newest day back → [1-day partial, 3-day full].
    const buckets = buildAxisBuckets(axisDates, 1);
    expect(buckets).toHaveLength(2);
    expect(buckets[0]?.partial).toBe(true);

    const { container } = render(UnifiedStripChart, {
      props: {
        axisDates,
        buckets,
        enabled,
        points: [
          // Leave the partial edge bucket (05-01) empty; fill the full bucket.
          {
            period_start: '2026-05-02',
            period_end: '2026-05-02',
            entry_count: 1,
            mood_avg: 4,
            energy_avg: 3,
            stress_avg: 3,
            sleep_quality_avg: null,
          },
          {
            period_start: '2026-05-04',
            period_end: '2026-05-04',
            entry_count: 1,
            mood_avg: 4,
            energy_avg: 3,
            stress_avg: 3,
            sleep_quality_avg: null,
          },
        ],
      },
    });

    const moodCells = container.querySelectorAll('[data-metric="mood_avg"] .strip__cell');
    expect(moodCells).toHaveLength(2);
    // Empty partial bucket → no data → transparent.
    expect(Number(moodCells[0]?.getAttribute('opacity'))).toBe(0);
    // Full bucket with logged data → visible.
    expect(Number(moodCells[1]?.getAttribute('opacity'))).toBeGreaterThan(0);
  });

  it('zooms into a multi-day bucket cell instead of opening its first day (#482)', async () => {
    const zoomInBucket = vi.fn();
    const selectDate = vi.fn();
    const axisDates = ['2026-05-01', '2026-05-02', '2026-05-03'];
    const buckets = buildAxisBuckets(axisDates, 1); // one 3-day bucket

    const { container } = render(UnifiedStripChart, {
      props: {
        axisDates,
        buckets,
        enabled,
        points: [
          {
            period_start: '2026-05-01',
            period_end: '2026-05-01',
            entry_count: 1,
            mood_avg: 4,
            energy_avg: 3,
            stress_avg: 3,
            sleep_quality_avg: null,
          },
        ],
      },
      events: { zoomInBucket, selectDate },
    });

    const cell = container.querySelector('[data-metric="mood_avg"] .strip__cell');
    await fireEvent.click(cell as Element);

    expect(zoomInBucket).toHaveBeenCalledTimes(1);
    expect(zoomInBucket.mock.calls[0][0].detail.bucket.dates).toHaveLength(3);
    // Must not open the bucket's first (possibly empty) day.
    expect(selectDate).not.toHaveBeenCalled();
  });

  it('opens the day for a single-day cell (#482)', async () => {
    const zoomInBucket = vi.fn();
    const selectDate = vi.fn();
    const axisDates = ['2026-05-01', '2026-05-02'];
    const buckets = buildAxisBuckets(axisDates, 0); // single-day buckets

    const { container } = render(UnifiedStripChart, {
      props: {
        axisDates,
        buckets,
        enabled,
        points: [
          {
            period_start: '2026-05-01',
            period_end: '2026-05-01',
            entry_count: 1,
            mood_avg: 4,
            energy_avg: 3,
            stress_avg: 3,
            sleep_quality_avg: null,
          },
        ],
      },
      events: { zoomInBucket, selectDate },
    });

    const cell = container.querySelector('[data-metric="mood_avg"] .strip__cell');
    await fireEvent.click(cell as Element);

    expect(selectDate).toHaveBeenCalledTimes(1);
    expect(selectDate.mock.calls[0][0].detail.date).toBe('2026-05-01');
    expect(zoomInBucket).not.toHaveBeenCalled();
  });
});

describe('UnifiedStripChart sleep-duration scale (#928 D3)', () => {
  const sleepEnabled = { ...enabled, sleep_minutes_avg: true };

  function sleepPoints(minutes: readonly (number | null)[]) {
    return minutes.map((value, index) => ({
      period_start: `2026-05-${String(index + 1).padStart(2, '0')}`,
      period_end: `2026-05-${String(index + 1).padStart(2, '0')}`,
      entry_count: 1,
      mood_avg: 3,
      energy_avg: 3,
      stress_avg: 3,
      sleep_quality_avg: null,
      sleep_minutes_avg: value,
    }));
  }

  function sleepCells(container: HTMLElement) {
    return Array.from(container.querySelectorAll('[data-metric="sleep_minutes_avg"] .strip__cell'));
  }

  it("reads a short sleeper's usual night as neutral, not as a deficit", () => {
    // Fourteen 5 h nights and one 8 h night. The scale this replaced fixed its
    // neutral point at 360 min, so every 5 h night was drawn on the negative
    // side — a recommendation rendered as data.
    const minutes = [...Array.from({ length: 14 }, () => 300), 480];
    const { container } = render(UnifiedStripChart, {
      props: {
        axisDates: sleepPoints(minutes).map((point) => point.period_start),
        enabled: sleepEnabled,
        points: sleepPoints(minutes),
      },
    });

    const cells = sleepCells(container);
    expect(cells).toHaveLength(15);
    expect(cells.slice(0, 14).map((cell) => cell.getAttribute('data-sign'))).toEqual(
      Array.from({ length: 14 }, () => 'mid')
    );
    expect(cells[14]?.getAttribute('data-sign')).toBe('pos');
  });

  it('marks nights on both sides of the personal median', () => {
    const minutes = [
      ...Array.from({ length: 7 }, () => 300),
      ...Array.from({ length: 7 }, () => 540),
    ];
    const { container } = render(UnifiedStripChart, {
      props: {
        axisDates: sleepPoints(minutes).map((point) => point.period_start),
        enabled: sleepEnabled,
        points: sleepPoints(minutes),
      },
    });

    const signs = sleepCells(container).map((cell) => cell.getAttribute('data-sign'));
    expect(new Set(signs)).toEqual(new Set(['neg', 'pos']));
  });

  it('states what the shading is based on', () => {
    const minutes = Array.from({ length: 14 }, () => 420);
    const { getByTestId } = render(UnifiedStripChart, {
      props: {
        axisDates: sleepPoints(minutes).map((point) => point.period_start),
        enabled: sleepEnabled,
        points: sleepPoints(minutes),
      },
    });

    expect(getByTestId('strip-sleep-basis').textContent).toContain('trends.sleep_scale.baseline');
  });

  it('encodes length only, and says so, while the history is too thin', () => {
    const minutes = [300, 420, 540];
    const { container, getByTestId } = render(UnifiedStripChart, {
      props: {
        axisDates: sleepPoints(minutes).map((point) => point.period_start),
        enabled: sleepEnabled,
        points: sleepPoints(minutes),
      },
    });

    const cells = sleepCells(container);
    expect(cells.map((cell) => cell.getAttribute('data-sign'))).toEqual(['seq', 'seq', 'seq']);
    expect(Number(cells[0]?.getAttribute('opacity'))).toBeLessThan(
      Number(cells[2]?.getAttribute('opacity'))
    );
    expect(getByTestId('strip-sleep-basis').textContent).toContain(
      'trends.sleep_scale.no_baseline'
    );
  });

  it('keeps nights longer than 12 h distinct instead of clamping them together', () => {
    // The shared 1–5 sleep domain tops out at SLEEP_MINUTES_CHART_MAX (720),
    // but the entry schema accepts up to 24 h. Encoding through it made a 13 h
    // and a 16 h night identical, and labelled both "12 h" (#972 review).
    const minutes = [...Array.from({ length: 14 }, () => 420), 780, 960];
    const { container } = render(UnifiedStripChart, {
      props: {
        axisDates: sleepPoints(minutes).map((point) => point.period_start),
        enabled: sleepEnabled,
        points: sleepPoints(minutes),
      },
    });

    const cells = sleepCells(container);
    const thirteen = cells[14];
    const sixteen = cells[15];

    expect(thirteen?.getAttribute('aria-label')).toContain('13 h');
    expect(sixteen?.getAttribute('aria-label')).toContain('16 h');
    expect(Number(sixteen?.getAttribute('opacity'))).toBeGreaterThan(
      Number(thirteen?.getAttribute('opacity'))
    );
  });

  it('labels a sleep cell with the duration it stands for, not a 1–5 position', () => {
    const minutes = [430];
    const { container } = render(UnifiedStripChart, {
      props: {
        axisDates: ['2026-05-01'],
        enabled: sleepEnabled,
        points: sleepPoints(minutes),
      },
    });

    expect(sleepCells(container)[0]?.getAttribute('aria-label')).toContain('7 h 10 min');
  });
});
