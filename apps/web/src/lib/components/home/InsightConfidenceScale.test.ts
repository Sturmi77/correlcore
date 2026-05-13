import { render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import InsightConfidenceScale from './InsightConfidenceScale.svelte';

vi.mock('svelte-i18n', async () => {
  const { readable } = await import('svelte/store');

  return {
    _: readable((key: string, options?: { values?: { n?: number } }) => {
      if (key === 'home.confidence_scale.entry_count')
        return `based on ${options?.values?.n} entries`;
      return key;
    }),
  };
});

const cases = [
  { entryCount: 0, confidenceScore: 0.05, currentTier: 'none', expected: '5%' },
  { entryCount: 3, confidenceScore: 0.2, currentTier: 'early', expected: '20%' },
  { entryCount: 8, confidenceScore: 0.4, currentTier: 'preliminary', expected: '40%' },
  { entryCount: 15, confidenceScore: 0.65, currentTier: 'developing', expected: '65%' },
  { entryCount: 30, confidenceScore: 0.9, currentTier: 'robust', expected: '90%' },
  { entryCount: 100, confidenceScore: 1, currentTier: 'robust', expected: '100%' },
] as const;

describe('InsightConfidenceScale', () => {
  it.each(cases)('renders boundary state for $entryCount entries', (props) => {
    render(InsightConfidenceScale, { props });

    const fill = screen.getByTestId('insight-confidence-fill');
    expect(fill.getAttribute('style')).toContain(`width: ${props.expected}`);
    expect(screen.getByText(`home.confidence_scale.tier.${props.currentTier}`)).toBeTruthy();
    expect(screen.getByText(`based on ${props.entryCount} entries`)).toBeTruthy();
  });

  it('clamps invalid score inputs', () => {
    render(InsightConfidenceScale, {
      props: { confidenceScore: 2, currentTier: 'robust', entryCount: 120 },
    });

    expect(screen.getByTestId('insight-confidence-fill').getAttribute('style')).toContain(
      'width: 100%'
    );
  });
});
