import { render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import type { TagHeatmapResponse } from '$lib/api/stats';
import TrendsComparePanel from './TrendsComparePanel.svelte';

vi.mock('svelte-i18n', async () => {
  const { readable } = await import('svelte/store');

  return {
    _: readable((key: string) => key),
  };
});

vi.mock('$app/environment', () => ({
  browser: false,
}));

const enabled = { mood_avg: true, energy_avg: true, stress_avg: true };

const pointsWithEntries = [
  {
    period_start: '2026-05-01',
    period_end: '2026-05-01',
    entry_count: 1,
    mood_avg: 3,
    energy_avg: 4,
    stress_avg: 2,
  },
];

const pointsWithoutEntries = [
  {
    period_start: '2026-05-01',
    period_end: '2026-05-01',
    entry_count: 0,
    mood_avg: null,
    energy_avg: null,
    stress_avg: null,
  },
];

const tagHeatmap: TagHeatmapResponse = {
  start_date: '2026-05-01',
  end_date: '2026-05-01',
  tags: [
    {
      tag_id: 't1',
      name: 'Sport',
      slug: 'sport',
      category: 'sport',
      color: null,
      days: [{ date: '2026-05-01', count: 1 }],
    },
  ],
};

describe('TrendsComparePanel', () => {
  it('hides Kontextzeilen when the selected range has no entries', () => {
    const { container } = render(TrendsComparePanel, {
      props: {
        points: pointsWithoutEntries,
        range: 'week',
        enabled,
        tagHeatmap,
        showTags: true,
        loading: false,
        compactChrome: true,
      },
    });

    expect(container.querySelector('.compare-heatmap')).toBeNull();
    expect(screen.queryByText('trends.compare.heatmap_heading')).toBeNull();
  });

  it('shows Kontextzeilen when the selected range has entries', () => {
    const { container } = render(TrendsComparePanel, {
      props: {
        points: pointsWithEntries,
        range: 'week',
        enabled,
        tagHeatmap,
        showTags: true,
        loading: false,
        compactChrome: true,
      },
    });

    expect(container.querySelector('.compare-heatmap')).toBeTruthy();
    expect(screen.getByText('trends.compare.heatmap_heading')).toBeTruthy();
  });
});
