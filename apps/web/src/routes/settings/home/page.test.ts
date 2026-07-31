import { render, screen, fireEvent, waitFor } from '@testing-library/svelte';
import { describe, expect, it, vi, beforeEach } from 'vitest';
import Page from './+page.svelte';
import { DEFAULT_HOME_SECTIONS } from '$lib/utils/homeSections';

vi.mock('svelte-i18n', async () => {
  const { readable } = await import('svelte/store');
  return {
    _: readable((key: string) => key),
    locale: readable('en'),
  };
});

const { updateUserPreferencesMock } = vi.hoisted(() => ({
  updateUserPreferencesMock: vi.fn(
    async (payload: { home_sections?: typeof DEFAULT_HOME_SECTIONS }) => ({
      user_id: 'user-1',
      analytics_enabled: true,
      digest_enabled: false,
      onboarding_retro_completed: true,
      onboarding_profile_completed: true,
      onboarding_maturity_intro_seen: true,
      cycle_tracking_enabled: true,
      dismissed_insight_keys: [],
      reached_milestone_keys: [],
      last_seen_insight_at: null,
      home_sections: payload.home_sections ?? DEFAULT_HOME_SECTIONS,
      created_at: '2026-05-16T10:00:00Z',
      updated_at: '2026-05-16T10:00:00Z',
    })
  ),
}));

vi.mock('$lib/api/preferences', () => ({
  fetchUserPreferences: vi.fn(async () => ({
    user_id: 'user-1',
    analytics_enabled: true,
    digest_enabled: false,
    onboarding_retro_completed: true,
    onboarding_profile_completed: true,
    onboarding_maturity_intro_seen: true,
    cycle_tracking_enabled: true,
    dismissed_insight_keys: [],
    reached_milestone_keys: [],
    last_seen_insight_at: null,
    home_sections: DEFAULT_HOME_SECTIONS,
    created_at: '2026-05-16T10:00:00Z',
    updated_at: '2026-05-16T10:00:00Z',
  })),
  updateUserPreferences: updateUserPreferencesMock,
}));

describe('/settings/home layout editor', () => {
  beforeEach(() => {
    updateUserPreferencesMock.mockClear();
  });

  it('loads configurable sections and persists toggle changes', async () => {
    render(Page);

    expect(await screen.findByTestId('home-sections-editor')).toBeTruthy();
    expect(screen.getByTestId('home-section-row-daily_brief')).toBeTruthy();

    const toggle = screen.getByTestId('home-section-toggle-daily_brief') as HTMLInputElement;
    expect(toggle.checked).toBe(true);

    await fireEvent.click(toggle);

    await waitFor(() => {
      expect(updateUserPreferencesMock).toHaveBeenCalledWith({
        home_sections: expect.arrayContaining([
          expect.objectContaining({ key: 'daily_brief', enabled: false }),
        ]),
      });
    });
  });

  it('reorders sections via move-down control', async () => {
    render(Page);
    await screen.findByTestId('home-sections-editor');

    await fireEvent.click(screen.getByTestId('home-section-down-first_week_banner'));

    await waitFor(() => {
      expect(updateUserPreferencesMock).toHaveBeenCalledWith({
        home_sections: [
          { key: 'daily_brief', enabled: true },
          { key: 'first_week_banner', enabled: true },
          { key: 'work_context', enabled: true },
          { key: 'weekday_overview', enabled: true },
        ],
      });
    });
  });

  it('resets to the default layout', async () => {
    render(Page);
    await screen.findByTestId('home-sections-editor');

    await fireEvent.click(screen.getByTestId('home-sections-reset'));

    await waitFor(() => {
      expect(updateUserPreferencesMock).toHaveBeenCalledWith({
        home_sections: DEFAULT_HOME_SECTIONS,
      });
    });
  });
});
