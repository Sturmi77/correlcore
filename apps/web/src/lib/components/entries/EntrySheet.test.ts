import { render, screen, fireEvent } from '@testing-library/svelte';
import { readable } from 'svelte/store';
import { describe, expect, it, vi } from 'vitest';
import EntrySheet from './EntrySheet.svelte';

vi.mock('svelte-i18n', () => ({
  _: readable((key: string) => key),
}));

vi.mock('./EntryForm.svelte', () => ({
  default: class EntryFormMock {
    requestClose = vi.fn(async () => true);
    constructor(options: { target?: HTMLElement }) {
      if (options.target) {
        const el = document.createElement('div');
        el.setAttribute('data-testid', 'entry-form-mock');
        options.target.appendChild(el);
      }
    }
    $on() {
      return () => {};
    }
    $set() {}
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
    const { component } = render(EntrySheet, {
      props: { open: true, initialDate: '2026-05-15' },
    });
    await fireEvent.click(screen.getByTestId('entry-sheet-backdrop'));
    expect(component.open).toBe(false);
  });
});
