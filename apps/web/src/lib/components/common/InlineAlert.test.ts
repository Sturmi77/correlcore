import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/svelte';
import InlineAlert from './InlineAlert.svelte';

describe('InlineAlert', () => {
  it('uses alert semantics for errors', () => {
    render(InlineAlert, {
      props: {
        variant: 'error',
        message: 'Could not load data',
        testId: 'load-error',
      },
    });

    expect(screen.getByRole('alert')).toBeTruthy();
    expect(screen.getByTestId('load-error').textContent).toContain('Could not load data');
  });

  it('dispatches action clicks with a stable test id', async () => {
    const handler = vi.fn();
    render(InlineAlert, {
      props: {
        message: 'Try again',
        actionLabel: 'Retry',
        actionTestId: 'retry-action',
      },
      events: { action: handler },
    });

    await fireEvent.click(screen.getByTestId('retry-action'));

    expect(handler).toHaveBeenCalledOnce();
  });

  it('disables the action button while actionLoading is true (#755)', () => {
    render(InlineAlert, {
      props: {
        variant: 'warning',
        message: 'Insights are stale',
        actionLabel: 'Refresh now',
        actionTestId: 'stale-action',
        actionLoading: true,
      },
    });

    const button = screen.getByTestId('stale-action') as HTMLButtonElement;
    expect(button.disabled).toBe(true);
    expect(button.getAttribute('aria-busy')).toBe('true');
  });
});
