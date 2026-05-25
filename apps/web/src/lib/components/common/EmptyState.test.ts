import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/svelte';
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
});
