import { render } from '@testing-library/svelte';
import { tick } from 'svelte';
import type { Writable } from 'svelte/store';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
  closeEntrySheet,
  entrySheetSnapshot,
  resetEntrySheetStore,
} from '$lib/stores/entrySheet';
import GlobalEntrySheet from './GlobalEntrySheet.svelte';

type AuthTestState = {
  status: 'authenticated';
  user: { id: string; email: string; is_verified: boolean };
};

type PageTestState = {
  url: URL;
};

const testHelpers = vi.hoisted(() => ({
  authStore: null as Writable<AuthTestState> | null,
  pageStore: null as Writable<PageTestState> | null,
}));

vi.mock('$lib/stores/auth', async () => {
  const { writable } = await import('svelte/store');
  const auth = writable<AuthTestState>({
    status: 'authenticated',
    user: { id: 'user-1', email: 'user@example.com', is_verified: true },
  });
  testHelpers.authStore = auth;
  return { auth };
});

vi.mock('$app/stores', async () => {
  const { writable } = await import('svelte/store');
  const page = writable<PageTestState>({ url: new URL('http://localhost/') });
  testHelpers.pageStore = page;
  return { page };
});

vi.mock('svelte-i18n', async () => {
  const { readable } = await import('svelte/store');
  return {
    _: readable((key: string) => key),
  };
});

vi.mock('./EntrySheet.svelte', () => ({
  default: function EntrySheetMock(anchor: Element | Comment, props: Record<string, unknown> = {}) {
    const el = document.createElement('div');
    el.setAttribute('data-testid', 'entry-sheet-mock');

    const update = () => {
      el.setAttribute('data-open', String(Boolean(props.open)));
      el.setAttribute('data-date', String(props.initialDate ?? ''));
    };

    update();
    anchor.parentNode?.insertBefore(el, anchor);

    return {
      $on() {
        return () => {};
      },
      $set(nextProps: Record<string, unknown>) {
        props = { ...props, ...nextProps };
        update();
      },
      $destroy() {
        el.remove();
      },
    };
  },
}));

async function flushAsync(): Promise<void> {
  await Promise.resolve();
  await tick();
  await Promise.resolve();
  await tick();
}

function navigateWithOpenEntry(date: string): void {
  window.history.pushState({}, '', `/?openEntry=1&date=${date}`);
  testHelpers.pageStore?.set({ url: new URL(window.location.href) });
}

describe('GlobalEntrySheet openEntry query handling', () => {
  beforeEach(() => {
    resetEntrySheetStore();
    window.history.replaceState({}, '', '/');
    testHelpers.authStore?.set({
      status: 'authenticated',
      user: { id: 'user-1', email: 'user@example.com', is_verified: true },
    });
    testHelpers.pageStore?.set({ url: new URL(window.location.href) });
  });

  afterEach(() => {
    resetEntrySheetStore();
    window.history.replaceState({}, '', '/');
    vi.clearAllMocks();
  });

  it('handles a fresh openEntry query after the sheet was closed in the same session', async () => {
    navigateWithOpenEntry('2026-06-01');
    render(GlobalEntrySheet);
    await flushAsync();

    expect(entrySheetSnapshot()).toMatchObject({ open: true, date: '2026-06-01' });
    expect(window.location.search).toBe('');

    closeEntrySheet();
    await flushAsync();
    expect(entrySheetSnapshot().open).toBe(false);

    navigateWithOpenEntry('2026-06-02');
    await flushAsync();

    expect(entrySheetSnapshot()).toMatchObject({ open: true, date: '2026-06-02' });
    expect(window.location.search).toBe('');
  });
});
