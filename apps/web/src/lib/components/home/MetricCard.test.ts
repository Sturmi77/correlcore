import { render, screen } from '@testing-library/svelte';
import { describe, expect, it } from 'vitest';
import MetricCard from './MetricCard.svelte';

describe('MetricCard', () => {
  it('renders an importable metric definition with its unit', () => {
    const { container } = render(MetricCard, {
      props: { metric: 'count', label: 'Entries', value: '5', unit: '/7' },
    });

    expect(screen.getByText('Entries')).toBeTruthy();
    expect(container.textContent).toContain('5');
    expect(screen.getByText('/7')).toBeTruthy();
    expect(container.querySelector('[data-metric="count"]')).toBeTruthy();
  });

  it('exposes its loading state', () => {
    const { container } = render(MetricCard, {
      props: { metric: 'energy', label: 'Energy', value: '3.2', loading: true },
    });

    expect(container.querySelector('[data-loading="true"]')).toBeTruthy();
  });
});
