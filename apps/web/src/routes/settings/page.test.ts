import { render, screen, fireEvent, waitFor } from '@testing-library/svelte';
import { describe, expect, it, vi, beforeEach } from 'vitest';
import Page from './+page.svelte';
import { devMode } from '$lib/stores/devMode';

vi.mock('svelte-i18n', async () => {
  const { readable } = await import('svelte/store');
  return {
    _: readable((key: string) => key),
    locale: readable('de'),
  };
});

vi.mock('$lib/stores/auth', async () => {
  const { readable } = await import('svelte/store');
  return {
    auth: readable({
      status: 'authenticated',
      user: { id: 'user-1', email: 'user@example.com' },
    }),
    // No is_admin → the admin entry stays hidden (gating check below).
    currentUser: readable({ id: 'user-1', email: 'user@example.com' }),
  };
});

vi.mock('$app/navigation', () => ({
  goto: vi.fn(),
}));

vi.mock('$lib/api/dev', () => ({
  fetchDevInfo: vi.fn(async () => {
    throw Object.assign(new Error('not found'), { status: 404 });
  }),
}));

describe('/settings hub (#694 IA)', () => {
  beforeEach(() => {
    devMode.set(false);
    localStorage.clear();
  });

  it('renders the four category entries and no inline forms', async () => {
    render(Page);

    expect(await screen.findByTestId('settings-cat-data')).toBeTruthy();
    expect(screen.getByTestId('settings-cat-analysis')).toBeTruthy();
    expect(screen.getByTestId('settings-cat-privacy')).toBeTruthy();
    expect(screen.getByTestId('settings-cat-appearance')).toBeTruthy();

    // The forms moved to the sub-pages — the hub must not carry them anymore.
    expect(screen.queryByTestId('regenerate-insights')).toBeNull();
    expect(screen.queryByTestId('cycle-delete-data')).toBeNull();
    expect(screen.queryByTestId('settings-delete-account')).toBeNull();
    expect(screen.queryByTestId('settings-language-control')).toBeNull();
  });

  it('links each category to its real sub-route', async () => {
    render(Page);

    expect((await screen.findByTestId('settings-cat-data')).getAttribute('href')).toBe(
      '/settings/data'
    );
    expect(screen.getByTestId('settings-cat-analysis').getAttribute('href')).toBe(
      '/settings/analysis'
    );
    expect(screen.getByTestId('settings-cat-privacy').getAttribute('href')).toBe(
      '/settings/privacy'
    );
    expect(screen.getByTestId('settings-cat-appearance').getAttribute('href')).toBe(
      '/settings/appearance'
    );
  });

  it('keeps the admin entry gated behind is_admin', async () => {
    render(Page);
    await screen.findByTestId('settings-cat-data');
    // currentUser mock has no is_admin → entry hidden.
    expect(screen.queryByTestId('settings-section-admin')).toBeNull();
  });

  it('keeps developer controls hidden until the 7x tap unlock', async () => {
    render(Page);

    expect(screen.queryByTestId('developer-section')).toBeNull();

    const version = screen.getByTestId('version-string');
    for (let i = 0; i < 7; i++) {
      await fireEvent.click(version);
    }

    await waitFor(() => {
      expect(screen.getByTestId('developer-section')).toBeTruthy();
    });
    expect(screen.getByTestId('force-viz-toggle')).toBeTruthy();
    await waitFor(() => {
      expect(screen.getByTestId('developer-backend-unavailable-hint')).toBeTruthy();
    });
  });

  it('shows developer section on load when dev mode was persisted', async () => {
    localStorage.setItem('dev_mode_enabled', 'true');
    devMode.set(true);

    render(Page);

    expect(await screen.findByTestId('developer-section')).toBeTruthy();
    expect(screen.getByTestId('force-viz-toggle')).toBeTruthy();
  });

  it('applies the selected developer phase preset entry count', async () => {
    render(Page);

    const version = screen.getByTestId('version-string');
    for (let i = 0; i < 7; i++) {
      await fireEvent.click(version);
    }

    const phaseSelect = await screen.findByTestId('developer-phase-select');
    await fireEvent.change(phaseSelect, { target: { value: 'robust' } });
    await fireEvent.click(screen.getByText('settings.developer.advanced'));

    await waitFor(() => {
      expect((screen.getByTestId('developer-entry-count') as HTMLInputElement).value).toBe('42');
    });
  });
});
