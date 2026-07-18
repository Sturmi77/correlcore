import { render, screen, fireEvent, waitFor } from '@testing-library/svelte';
import { describe, expect, it, vi, beforeEach } from 'vitest';
import Page from './+page.svelte';
import { devMode } from '$lib/stores/devMode';

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
    digest_enabled: true,
    onboarding_retro_completed: true,
    onboarding_profile_completed: true,
    onboarding_maturity_intro_seen: true,
    dismissed_insight_keys: [],
    reached_milestone_keys: [],
    last_seen_insight_at: null,
    created_at: '2026-05-16T10:00:00Z',
    updated_at: '2026-05-16T10:00:00Z',
  })),
  updateUserPreferences: vi.fn(async (payload) => ({
    user_id: 'user-1',
    analytics_enabled: payload.analytics_enabled ?? true,
    digest_enabled: payload.digest_enabled ?? false,
    onboarding_retro_completed: true,
    onboarding_profile_completed: true,
    onboarding_maturity_intro_seen: true,
    dismissed_insight_keys: [],
    reached_milestone_keys: [],
    last_seen_insight_at: null,
    created_at: '2026-05-16T10:00:00Z',
    updated_at: '2026-05-16T10:00:00Z',
  })),
}));

vi.mock('$lib/api/user', () => ({
  deleteAccount: vi.fn(async () => undefined),
}));

vi.mock('$lib/api/insights', () => ({
  regenerateInsights: vi.fn(async () => ({
    status: 'ok',
    generated_for_date: '2026-07-13',
    insight_count: 5,
    tag_clusters_status: 'ok',
    trigger_source: 'user_regenerate',
  })),
}));

vi.mock('$lib/api/consents', () => ({
  HEALTH_CONNECT_CONSENT_TYPE: 'health_connect',
  HEALTH_CONNECT_CONSENT_VERSION: '1',
  fetchUserConsents: vi.fn(async () => ({
    current: [],
    history: [],
  })),
  recordUserConsent: vi.fn(),
  revokeUserConsent: vi.fn(),
}));

describe('/settings Sprint 7', () => {
  beforeEach(() => {
    devMode.set(false);
    localStorage.clear();
  });

  it('renders the canonical settings sections', async () => {
    render(Page);

    expect(await screen.findByTestId('settings-section-vocabulary')).toBeTruthy();
    expect(screen.getByTestId('settings-vocab-tags')).toBeTruthy();
    expect(screen.getByTestId('settings-vocab-symptoms')).toBeTruthy();
    expect(screen.getByTestId('settings-vocab-habits')).toBeTruthy();
    expect(screen.getByTestId('settings-delete-account')).toBeTruthy();
    expect(screen.getByTestId('settings-privacy-policy')).toBeTruthy();
    expect(screen.getByTestId('settings-section-export')).toBeTruthy();
    expect(screen.getByTestId('settings-section-analysis')).toBeTruthy();
    expect(screen.getByTestId('settings-section-privacy')).toBeTruthy();
    expect(screen.getByTestId('settings-health-connect-consent')).toBeTruthy();
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

  it('switches locale through the segmented language control', async () => {
    render(Page);

    await fireEvent.click(screen.getByTestId('language-en'));

    await waitFor(() => {
      expect(screen.getByTestId('language-en').getAttribute('aria-pressed')).toBe('true');
    });
  });

  it('shows regenerate insights control in analysis section', async () => {
    render(Page);

    expect(await screen.findByTestId('regenerate-insights')).toBeTruthy();
  });
});
