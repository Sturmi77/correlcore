import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/svelte';
import DataState from './DataState.svelte';

describe('DataState', () => {
  it('renders loading state with busy semantics', () => {
    render(DataState, {
      props: {
        state: 'loading',
        loadingText: 'Loading tags',
        testId: 'tag-loading',
      },
    });

    expect(screen.getByTestId('tag-loading').getAttribute('aria-busy')).toBe('true');
    expect(screen.getByText('Loading tags')).toBeTruthy();
  });

  it('dispatches retry from error state', async () => {
    const handler = vi.fn();
    render(DataState, {
      props: {
        state: 'error',
        error: 'Network failed',
        retryLabel: 'Retry',
        actionTestId: 'retry-state',
      },
      events: { retry: handler },
    });

    await fireEvent.click(screen.getByTestId('retry-state'));

    expect(handler).toHaveBeenCalledOnce();
  });

  it('renders empty state copy', () => {
    render(DataState, {
      props: {
        state: 'empty',
        emptyTitle: 'Nothing here',
        emptyBody: 'Add data to continue.',
        testId: 'empty-data',
      },
    });

    expect(screen.getByTestId('empty-data').textContent).toContain('Nothing here');
    expect(screen.getByText('Add data to continue.')).toBeTruthy();
  });

  it('renders a partial-data warning without error semantics', () => {
    render(DataState, {
      props: {
        state: 'partial',
        partialMessage: 'Some comparison data is unavailable.',
        testId: 'partial-data',
      },
    });

    expect(screen.getByTestId('partial-data').textContent).toContain(
      'Some comparison data is unavailable.'
    );
    expect(screen.getByTestId('partial-data').querySelector('[role="alert"]')).toBeNull();
  });
});
