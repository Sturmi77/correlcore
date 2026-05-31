import { render } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import UnifiedStripChart from './UnifiedStripChart.svelte';

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
});
