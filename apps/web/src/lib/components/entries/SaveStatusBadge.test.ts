import { fireEvent, render, screen } from '@testing-library/svelte';
import { readable } from 'svelte/store';
import { describe, expect, it, vi } from 'vitest';
import SaveStatusBadge from './SaveStatusBadge.svelte';

vi.mock('svelte-i18n', () => ({
  _: readable((key: string) => key),
}));

describe('SaveStatusBadge', () => {
  it('uses the explicit offline copy and preserves retry', async () => {
    const retry = vi.fn();
    render(SaveStatusBadge, {
      props: { status: 'error', offline: true, onRetry: retry },
    });

    expect(screen.getByText('entry.autosave.offline')).toBeTruthy();
    expect(screen.queryByText('entry.autosave.error')).toBeNull();

    await fireEvent.click(screen.getByTestId('save-status-retry'));
    expect(retry).toHaveBeenCalledOnce();
  });
});
