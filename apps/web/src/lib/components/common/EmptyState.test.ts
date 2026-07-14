import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/svelte';
import EmptyState from './EmptyState.svelte';

describe('EmptyState', () => {
  it('renders title, body, and optional action', () => {
    render(EmptyState, {
      props: {
        title: 'No entries yet',
        body: 'Create an entry to start the timeline.',
        actionLabel: 'Create entry',
        actionHref: '/',
        testId: 'empty-state',
      },
    });

    expect(screen.getByTestId('empty-state').textContent).toContain('No entries yet');
    expect(screen.getByText('Create an entry to start the timeline.')).toBeTruthy();
    expect(screen.getByRole('link', { name: 'Create entry' }).getAttribute('href')).toBe('/');
  });

  it('dispatches secondaryAction when the secondary CTA is clicked', async () => {
    const handler = vi.fn();
    render(EmptyState, {
      props: {
        title: 'No insights yet',
        actionLabel: 'Go home',
        actionHref: '/',
        secondaryActionLabel: 'Refresh insights',
        testId: 'empty-state',
      },
      events: { secondaryAction: handler },
    });

    await fireEvent.click(screen.getByTestId('empty-state-secondary-cta'));
    expect(handler).toHaveBeenCalledOnce();
  });
});
