import { render, screen, fireEvent, waitFor } from '@testing-library/svelte';
import { readable } from 'svelte/store';
import { describe, expect, it, vi } from 'vitest';
import EntrySheet from './EntrySheet.svelte';

vi.mock('svelte-i18n', () => ({
  _: readable((key: string) => key),
}));

vi.mock('./EntryForm.svelte', () => ({
  default: function EntryFormMock(anchor: Element | Comment) {
    const el = document.createElement('div');
    el.setAttribute('data-testid', 'entry-form-mock');
    anchor.parentNode?.insertBefore(el, anchor);

    return {
      requestClose: vi.fn(async () => true),
      $on() {
        return () => {};
      },
      $set() {},
      $destroy() {
        el.remove();
      },
    };
  },
}));

describe('EntrySheet', () => {
  it('renders dialog when open', () => {
    render(EntrySheet, {
      props: { open: true, initialDate: '2026-05-15' },
    });
    expect(screen.getByTestId('entry-sheet')).toBeTruthy();
    expect(screen.getByRole('dialog')).toBeTruthy();
  });

  it('is hidden when closed', () => {
    render(EntrySheet, {
      props: { open: false, initialDate: '2026-05-15' },
    });
    expect(screen.queryByTestId('entry-sheet')).toBeNull();
  });

  it('closes on backdrop click', async () => {
    render(EntrySheet, {
      props: { open: true, initialDate: '2026-05-15' },
    });
    await fireEvent.click(screen.getByTestId('entry-sheet-backdrop'));
    await waitFor(() => {
      expect(screen.queryByTestId('entry-sheet')).toBeNull();
    });
  });
});
