import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import CorrelationHint from './CorrelationHint.svelte';

vi.mock('svelte-i18n', async () => {
  const { readable } = await import('svelte/store');
  return { _: readable((key: string) => key) };
});

describe('CorrelationHint', () => {
  it('renders the hint with a <=1-click link to the canonical disclaimer (#632)', () => {
    render(CorrelationHint);
    expect(screen.getByTestId('correlation-hint')).toBeTruthy();
    const link = screen.getByTestId('correlation-hint-link') as HTMLAnchorElement;
    expect(link.getAttribute('href')).toBe('/insights/disclaimer');
  });
});
