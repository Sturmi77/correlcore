import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import AnalysisCrossLink from './AnalysisCrossLink.svelte';
import type { InsightResponse } from '$lib/api/insights';

vi.mock('svelte-i18n', () => ({
  _: {
    subscribe: (
      run: (
        formatter: (key: string, options?: { values?: Record<string, unknown> }) => string
      ) => void
    ) => {
      run((key: string, options?: { values?: Record<string, unknown> }) => {
        if (key === 'analysis.cross_link.top_insight') {
          return `Top insight: ${options?.values?.label}`;
        }
        if (key === 'analysis.cross_link.view_trends') return 'View related trends';
        return key;
      });
      return () => undefined;
    },
  },
}));

const insight = {
  id: 'i1',
  metric: 'energy',
  subject_label: 'Energy',
} as InsightResponse;

describe('AnalysisCrossLink', () => {
  it('links to insights with the top finding label', () => {
    render(AnalysisCrossLink, { props: { insight, direction: 'to-insights' } });
    const link = screen.getByTestId('analysis-cross-link-insights');
    expect(link.getAttribute('href')).toBe('/insights');
    expect(screen.getByTestId('analysis-cross-link-insights').textContent).toContain(
      'Top insight: Energy'
    );
  });

  it('links to trends from the featured insight', () => {
    render(AnalysisCrossLink, { props: { insight, direction: 'to-trends' } });
    const link = screen.getByTestId('analysis-cross-link-trends');
    expect(link.getAttribute('href')).toBe('/trends');
    expect(link.textContent).toContain('View related trends');
  });
});
