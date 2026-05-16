import { render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import InsightQualityMeter from './InsightQualityMeter.svelte';

vi.mock('svelte-i18n', async () => {
  const { readable } = await import('svelte/store');
  return {
    _: readable((key: string, options?: { values?: Record<string, string | number> }) => {
      const values = options?.values ?? {};
      const map: Record<string, string> = {
        'insights.quality_meter.heading': 'Insight quality',
        'insights.quality_meter.getting_started':
          'Your data is being collected. First patterns become visible around 30 entries.',
        'insights.quality_meter.building_pace': `${values.current}/${values.target}. At your current tracking pace: ca. ${values.weeks} weeks until first insight.`,
        'insights.quality_meter.building_no_recent': `${values.current}/${values.target}. No recent entries found. Estimated time to first insight cannot be calculated.`,
        'insights.quality_meter.ready_low':
          'First insight visible. The confidence label is shown per insight.',
        'insights.quality_meter.ready_full': 'Full insights are available.',
        'insights.quality_meter.entry_total': `Based on ${values.n} entries`,
        'insights.confidence_label.strong_finding': 'Strong finding',
      };
      return map[key] ?? key;
    }),
  };
});

function dates(count: number, startDay = 1): string[] {
  return Array.from({ length: count }, (_, idx) => {
    const date = new Date(Date.UTC(2026, 4, startDay + idx));
    return date.toISOString().slice(0, 10);
  });
}

describe('InsightQualityMeter', () => {
  it('renders 0-3 entries without a progress fraction or estimate', () => {
    render(InsightQualityMeter, {
      props: {
        dayEntryDates: ['2026-05-01', '2026-05-02', '2026-05-03'],
        asOfIso: '2026-05-16',
      },
    });

    expect(screen.getByTestId('insight-quality-meter').getAttribute('data-stage')).toBe(
      'getting_started'
    );
    expect(screen.queryByTestId('insight-quality-fraction')).toBeNull();
    expect(screen.getByTestId('insight-quality-body').textContent).toContain(
      'Your data is being collected'
    );
  });

  it('renders 4-29 entries with pace estimate from recent entries', () => {
    render(InsightQualityMeter, {
      props: {
        dayEntryDates: [
          '2026-05-01',
          '2026-05-02',
          '2026-05-03',
          '2026-05-04',
          '2026-05-05',
          '2026-05-06',
          '2026-05-07',
          '2026-05-08',
          '2026-05-09',
          '2026-05-10',
        ],
        asOfIso: '2026-05-14',
      },
    });

    expect(screen.getByTestId('insight-quality-meter').getAttribute('data-stage')).toBe(
      'building_with_pace'
    );
    expect(screen.getByTestId('insight-quality-fraction').textContent?.trim()).toBe('10/30');
    expect(screen.getByTestId('insight-quality-body').textContent).toContain('4 weeks');
  });

  it('renders 4-29 entries without an estimate when recent entries are absent', () => {
    render(InsightQualityMeter, {
      props: {
        dayEntryDates: ['2026-05-01', '2026-05-02', '2026-05-03', '2026-05-04'],
        asOfIso: '2026-06-01',
      },
    });

    expect(screen.getByTestId('insight-quality-meter').getAttribute('data-stage')).toBe(
      'building_no_recent'
    );
    expect(screen.getByTestId('insight-quality-body').textContent).toContain(
      'Estimated time to first insight cannot be calculated'
    );
  });

  it('renders the first insight stage from 30 entries', () => {
    render(InsightQualityMeter, {
      props: {
        dayEntryDates: dates(30),
        confidenceScore: 0.7,
        insightTier: 'developing',
        asOfIso: '2026-05-30',
      },
    });

    expect(screen.getByTestId('insight-quality-meter').getAttribute('data-stage')).toBe(
      'ready_low'
    );
    expect(screen.getByTestId('insight-quality-confidence-label').textContent?.trim()).toBe(
      'Strong finding'
    );
    expect(screen.getByTestId('insight-quality-meta').textContent).toContain('30 entries');
  });
});
