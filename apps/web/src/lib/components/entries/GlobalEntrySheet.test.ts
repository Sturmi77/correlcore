import { render, screen, waitFor } from '@testing-library/svelte';
import { tick } from 'svelte';
import type { Writable } from 'svelte/store';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { closeEntrySheet, entrySheetSnapshot, resetEntrySheetStore } from '$lib/stores/entrySheet';
import { isoDate } from '$lib/utils/entryForm';
import GlobalEntrySheet from './GlobalEntrySheet.svelte';

type AuthTestState =
  | {
      status: 'authenticated';
      user: { id: string; email: string; is_verified: boolean };
    }
  | { status: 'anonymous' };

type PageTestState = {
  url: URL;
};

const testHelpers = vi.hoisted(() => ({
  authStore: null as Writable<AuthTestState> | null,
  pageStore: null as Writable<PageTestState> | null,
  fetchUserProfile: vi.fn(),
  fetchUserPreferences: vi.fn(),
  fetchDashboardSummary: vi.fn(),
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

vi.mock('$lib/api/profile', () => ({
  fetchUserProfile: (...args: unknown[]) => testHelpers.fetchUserProfile(...args),
}));

vi.mock('$lib/api/preferences', () => ({
  fetchUserPreferences: (...args: unknown[]) => testHelpers.fetchUserPreferences(...args),
}));

vi.mock('$lib/api/dashboard', () => ({
  fetchDashboardSummary: (...args: unknown[]) => testHelpers.fetchDashboardSummary(...args),
}));

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
    // Svelte 5 passes live getters for props — keep the original object so
    // tests can read current values (spreading would freeze getter snapshots).
    (el as HTMLElement & { __entrySheetProps?: Record<string, unknown> }).__entrySheetProps = props;

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
        Object.assign(props, nextProps);
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

function navigateWithOpenEntry(date?: string): void {
  const path = date ? `/?openEntry=1&date=${date}` : '/?openEntry=1';
  window.history.pushState({}, '', path);
  testHelpers.pageStore?.set({ url: new URL(window.location.href) });
}

describe('GlobalEntrySheet openEntry query handling', () => {
  beforeEach(() => {
    resetEntrySheetStore();
    window.history.replaceState({}, '', '/');
    testHelpers.fetchUserProfile.mockResolvedValue({ work_context_typical: null });
    testHelpers.fetchUserPreferences.mockResolvedValue({
      user_id: 'user-1',
      cycle_tracking_enabled: true,
      onboarding_completed: true,
    });
    testHelpers.fetchDashboardSummary.mockResolvedValue({ entry_count: 3 });
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

  it('falls back to the local calendar day when openEntry has no date (#447 widget)', async () => {
    // correlcore://entries/new resolves to /?openEntry=1 with no date. Using
    // UTC here would open tomorrow after local evening in the Americas while
    // the widget (device tz) still shows "no entry today".
    navigateWithOpenEntry();
    render(GlobalEntrySheet);
    await flushAsync();

    expect(entrySheetSnapshot()).toMatchObject({ open: true, date: isoDate(new Date()) });
    expect(window.location.search).toBe('');
  });

  it('reloads work_context_typical when login switches accounts without an anonymous gap', async () => {
    // login()/setUser() can go A→B while status stays authenticated. A boolean
    // profileLoaded gate would keep A's typical and autosave it into B's entry.
    testHelpers.fetchUserProfile
      .mockResolvedValueOnce({ work_context_typical: 'office' })
      .mockResolvedValueOnce({ work_context_typical: 'remote' });

    testHelpers.authStore?.set({
      status: 'authenticated',
      user: { id: 'user-a', email: 'a@example.com', is_verified: true },
    });
    render(GlobalEntrySheet);

    const sheetProps = () =>
      (
        screen.getByTestId('entry-sheet-mock') as HTMLElement & {
          __entrySheetProps?: Record<string, unknown>;
        }
      ).__entrySheetProps;

    await waitFor(() => {
      expect(sheetProps()?.workContextTypical).toBe('office');
    });

    testHelpers.authStore?.set({
      status: 'authenticated',
      user: { id: 'user-b', email: 'b@example.com', is_verified: true },
    });

    await waitFor(() => {
      expect(sheetProps()?.workContextTypical).toBe('remote');
    });
    expect(testHelpers.fetchUserProfile).toHaveBeenCalledTimes(2);
  });
});
