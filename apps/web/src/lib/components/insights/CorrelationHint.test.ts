import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import CorrelationHint from './CorrelationHint.svelte';

vi.mock('svelte-i18n', async () => {
  const { readable } = await import('svelte/store');
  return { _: readable((key: string) => key) };
});

describe('CorrelationHint', () => {
  it('links to the canonical disclaimer, defaulting the return to /insights (#632)', () => {
    render(CorrelationHint);
    expect(screen.getByTestId('correlation-hint')).toBeTruthy();
    const link = screen.getByTestId('correlation-hint-link') as HTMLAnchorElement;
    expect(link.getAttribute('href')).toBe('/insights/disclaimer?return=%2Finsights');
  });

  it('encodes the origin surface into the return param so close returns there', () => {
    render(CorrelationHint, { props: { returnTo: '/insights/digest' } });
    const link = screen.getByTestId('correlation-hint-link') as HTMLAnchorElement;
    expect(link.getAttribute('href')).toBe('/insights/disclaimer?return=%2Finsights%2Fdigest');
  });
});
