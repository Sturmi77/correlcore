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
          },
          {
            period_start: '2026-05-02',
            period_end: '2026-05-02',
            entry_count: 1,
            mood_avg: 3,
            energy_avg: 3,
            stress_avg: 1,
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
          },
          {
            period_start: '2026-05-02',
            period_end: '2026-05-02',
            entry_count: 1,
            mood_avg: 4,
            energy_avg: 3,
            stress_avg: 3,
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
          },
          {
            period_start: '2026-05-04',
            period_end: '2026-05-04',
            entry_count: 1,
            mood_avg: 4,
            energy_avg: 3,
            stress_avg: 3,
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
