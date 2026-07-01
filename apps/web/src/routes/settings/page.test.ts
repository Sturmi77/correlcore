import { render, screen, fireEvent, waitFor } from '@testing-library/svelte';
import { describe, expect, it, vi, beforeEach } from 'vitest';
import Page from './+page.svelte';

vi.mock('svelte-i18n', async () => {
  const { readable, writable } = await import('svelte/store');
  return {
    _: readable((key: string) => key),
    locale: writable('de'),
  };
});

vi.mock('$lib/i18n', async () => {
  const i18n = await import('svelte-i18n');
  return {
    setAppLocale: vi.fn((nextLocale: string) => i18n.locale.set(nextLocale)),
  };
});

vi.mock('$lib/stores/auth', async () => {
  const { readable } = await import('svelte/store');
  return {
    auth: readable({
      status: 'authenticated',
      user: { id: 'user-1', email: 'user@example.com' },
    }),
    logout: vi.fn(async () => undefined),
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

vi.mock('$lib/api/export', () => ({
  downloadExport: vi.fn(),
  exportFilename: vi.fn((kind: string) => `export.${kind}`),
  saveBlob: vi.fn(),
}));

vi.mock('$lib/api/preferences', () => ({
  fetchUserPreferences: vi.fn(async () => ({
    user_id: 'user-1',
    analytics_enabled: true,
    onboarding_retro_completed: true,
    onboarding_profile_completed: true,
    dismissed_insight_keys: [],
    reached_milestone_keys: [],
    last_seen_insight_at: null,
    created_at: '2026-05-16T10:00:00Z',
    updated_at: '2026-05-16T10:00:00Z',
  })),
  updateUserPreferences: vi.fn(async (payload) => ({
    user_id: 'user-1',
    analytics_enabled: payload.analytics_enabled ?? true,
    onboarding_retro_completed: true,
    onboarding_profile_completed: true,
    dismissed_insight_keys: [],
    reached_milestone_keys: [],
    last_seen_insight_at: null,
    created_at: '2026-05-16T10:00:00Z',
    updated_at: '2026-05-16T10:00:00Z',
  })),
}));

describe('/settings Sprint 7', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('renders the canonical settings sections', async () => {
    render(Page);

    expect(await screen.findByTestId('settings-section-tracking')).toBeTruthy();
    expect(screen.getByTestId('settings-section-export')).toBeTruthy();
    expect(screen.getByTestId('settings-section-analysis')).toBeTruthy();
    expect(screen.getByTestId('settings-section-privacy')).toBeTruthy();
    expect(screen.getByTestId('settings-section-appearance')).toBeTruthy();
    expect(screen.getByTestId('settings-section-account')).toBeTruthy();
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
  });

  it('switches locale through the segmented language control', async () => {
    render(Page);

    await fireEvent.click(screen.getByTestId('language-en'));

    await waitFor(() => {
      expect(screen.getByTestId('language-en').getAttribute('aria-pressed')).toBe('true');
    });
  });
});
