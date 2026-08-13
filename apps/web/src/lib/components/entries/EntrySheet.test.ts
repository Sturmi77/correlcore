import { render, screen, fireEvent, waitFor } from '@testing-library/svelte';
import { readable, type Writable } from 'svelte/store';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import EntrySheet from './EntrySheet.svelte';

type AuthTestState =
  | {
      status: 'authenticated';
      user: { id: string; email: string; is_verified: boolean };
    }
  | { status: 'anonymous' };

const testHelpers = vi.hoisted(() => ({
  authStore: null as Writable<AuthTestState> | null,
}));

vi.mock('$lib/stores/auth', async () => {
  const { writable: w, derived } = await import('svelte/store');
  const auth = w<AuthTestState>({ status: 'anonymous' });
  testHelpers.authStore = auth;
  return {
    auth: { subscribe: auth.subscribe },
    currentUser: derived(auth, ($a) => ($a.status === 'authenticated' ? $a.user : null)),
  };
});

vi.mock('svelte-i18n', () => ({
  _: readable((key: string) => key),
}));

vi.mock('./EntryForm.svelte', () => ({
  default: function EntryFormMock(anchor: Element | Comment) {
    const el = document.createElement('div');
    el.setAttribute('data-testid', 'entry-form-mock');
    el.setAttribute('data-instance', String(crypto.randomUUID()));
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
  beforeEach(() => {
    testHelpers.authStore?.set({
      status: 'authenticated',
      user: { id: 'user-a', email: 'a@example.com', is_verified: true },
    });
  });

  afterEach(() => {
    testHelpers.authStore?.set({ status: 'anonymous' });
  });

  it('renders dialog when open', () => {
    render(EntrySheet, {
      props: { open: true, initialDate: '2026-05-15' },
    });
    const dialog = screen.getByTestId('entry-sheet');
    expect(dialog.tagName.toLowerCase()).toBe('dialog');
    expect(screen.getByTestId('entry-form-mock')).toBeTruthy();
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
    await fireEvent.click(screen.getByTestId('entry-sheet'));
    await waitFor(() => {
      expect(screen.queryByTestId('entry-sheet')).toBeNull();
    });
  });

  it('remounts EntryForm when the authenticated user changes without an anonymous gap', async () => {
    render(EntrySheet, {
      props: { open: true, initialDate: '2026-05-15' },
    });
    const first = screen.getByTestId('entry-form-mock').getAttribute('data-instance');
    expect(first).toBeTruthy();

    testHelpers.authStore?.set({
      status: 'authenticated',
      user: { id: 'user-b', email: 'b@example.com', is_verified: true },
    });

    await waitFor(() => {
      const second = screen.getByTestId('entry-form-mock').getAttribute('data-instance');
      expect(second).toBeTruthy();
      expect(second).not.toBe(first);
    });
  });
});
