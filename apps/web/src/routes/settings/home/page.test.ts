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
  updateUserPreferencesMock: vi.fn(async (payload: Record<string, unknown>) => ({
    user_id: 'user-1',
    analytics_enabled: true,
    digest_enabled: false,
    onboarding_retro_completed: true,
    onboarding_profile_completed: true,
    onboarding_maturity_intro_seen: true,
    cycle_tracking_enabled: true,
    home_weekday_day_trend_enabled: true,
    dismissed_insight_keys: [],
    reached_milestone_keys: [],
    last_seen_insight_at: null,
    home_sections: payload.home_sections ?? DEFAULT_HOME_SECTIONS,
    created_at: '2026-05-16T10:00:00Z',
    updated_at: '2026-05-16T10:00:00Z',
    ...payload,
  })),
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
    home_weekday_day_trend_enabled: true,
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
          { key: 'trends_summary', enabled: true },
        ],
      });
    });
  });

  it('does not fire a second PATCH until the in-flight reorder finishes (latest wins)', async () => {
    let resolveFirst: (() => void) | undefined;
    updateUserPreferencesMock.mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          resolveFirst = () =>
            resolve({
              user_id: 'user-1',
              analytics_enabled: true,
              digest_enabled: false,
              onboarding_retro_completed: true,
              onboarding_profile_completed: true,
              onboarding_maturity_intro_seen: true,
              cycle_tracking_enabled: true,
              home_weekday_day_trend_enabled: true,
              dismissed_insight_keys: [],
              reached_milestone_keys: [],
              last_seen_insight_at: null,
              home_sections: [
                { key: 'daily_brief', enabled: true },
                { key: 'first_week_banner', enabled: true },
                { key: 'work_context', enabled: true },
                { key: 'weekday_overview', enabled: true },
                { key: 'trends_summary', enabled: true },
              ],
              created_at: '2026-05-16T10:00:00Z',
              updated_at: '2026-05-16T10:00:00Z',
            });
        })
    );

    render(Page);
    await screen.findByTestId('home-sections-editor');

    await fireEvent.click(screen.getByTestId('home-section-down-first_week_banner'));
    await waitFor(() => {
      expect(updateUserPreferencesMock).toHaveBeenCalledTimes(1);
    });

    await fireEvent.click(screen.getByTestId('home-section-down-first_week_banner'));
    await Promise.resolve();
    await Promise.resolve();
    expect(updateUserPreferencesMock).toHaveBeenCalledTimes(1);

    resolveFirst?.();

    const latestOrder = [
      'daily_brief',
      'work_context',
      'first_week_banner',
      'weekday_overview',
      'trends_summary',
    ];

    await waitFor(() => {
      expect(updateUserPreferencesMock).toHaveBeenCalledTimes(2);
    });
    const lastPayload = (updateUserPreferencesMock.mock.calls.at(-1)?.[0]?.home_sections ?? []) as {
      key: string;
    }[];
    expect(lastPayload.map((section) => section.key)).toEqual(latestOrder);

    await waitFor(() => {
      const rows = screen.getAllByTestId(/^home-section-row-/);
      expect(rows.map((row) => row.getAttribute('data-testid'))).toEqual(
        latestOrder.map((key) => `home-section-row-${key}`)
      );
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

  it('persists the per-weekday trend caret toggle', async () => {
    render(Page);
    const toggle = (await screen.findByTestId('weekday-day-trend-toggle')) as HTMLInputElement;
    expect(toggle.checked).toBe(true);

    await fireEvent.click(toggle);

    await waitFor(() => {
      expect(updateUserPreferencesMock).toHaveBeenCalledWith({
        home_weekday_day_trend_enabled: false,
      });
    });
  });

  it('does not reset section order from a day-trend PATCH response', async () => {
    render(Page);
    await screen.findByTestId('home-sections-editor');
    await fireEvent.click(screen.getByTestId('home-section-down-first_week_banner'));
    await waitFor(() => {
      expect(updateUserPreferencesMock).toHaveBeenCalledWith(
        expect.objectContaining({
          home_sections: [
            { key: 'daily_brief', enabled: true },
            { key: 'first_week_banner', enabled: true },
            { key: 'work_context', enabled: true },
            { key: 'weekday_overview', enabled: true },
            { key: 'trends_summary', enabled: true },
          ],
        })
      );
    });

    await fireEvent.click(await screen.findByTestId('weekday-day-trend-toggle'));
    await waitFor(() => {
      expect(updateUserPreferencesMock).toHaveBeenCalledWith({
        home_weekday_day_trend_enabled: false,
      });
    });

    const rows = screen.getAllByTestId(/^home-section-row-/);
    expect(rows.map((row) => row.getAttribute('data-testid'))).toEqual([
      'home-section-row-daily_brief',
      'home-section-row-first_week_banner',
      'home-section-row-work_context',
      'home-section-row-weekday_overview',
      'home-section-row-trends_summary',
    ]);
  });
});
