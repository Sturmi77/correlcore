import { render, screen, fireEvent, waitFor } from '@testing-library/svelte';
import { describe, expect, it, vi, beforeEach } from 'vitest';
import Page from './+page.svelte';
import { DEFAULT_INSIGHT_SECTIONS } from '$lib/utils/insightSections';

vi.mock('svelte-i18n', async () => {
  const { readable } = await import('svelte/store');
  return {
    _: readable((key: string) => key),
    locale: readable('en'),
  };
});

const { updateUserPreferencesMock } = vi.hoisted(() => ({
  updateUserPreferencesMock: vi.fn(
    async (payload: { insight_sections?: typeof DEFAULT_INSIGHT_SECTIONS }) => ({
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
      insight_sections: payload.insight_sections ?? DEFAULT_INSIGHT_SECTIONS,
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
    insight_sections: DEFAULT_INSIGHT_SECTIONS,
    created_at: '2026-05-16T10:00:00Z',
    updated_at: '2026-05-16T10:00:00Z',
  })),
  updateUserPreferences: updateUserPreferencesMock,
}));

describe('/settings/insights layout editor', () => {
  beforeEach(() => {
    updateUserPreferencesMock.mockClear();
  });

  it('loads configurable sections and persists toggle changes', async () => {
    render(Page);

    expect(await screen.findByTestId('insights-sections-editor')).toBeTruthy();
    expect(screen.getByTestId('insights-section-row-lag_heatmap')).toBeTruthy();

    const toggle = screen.getByTestId('insights-section-toggle-lag_heatmap') as HTMLInputElement;
    expect(toggle.checked).toBe(true);

    await fireEvent.click(toggle);

    await waitFor(() => {
      expect(updateUserPreferencesMock).toHaveBeenCalledWith({
        insight_sections: expect.arrayContaining([
          expect.objectContaining({ key: 'lag_heatmap', enabled: false }),
        ]),
      });
    });
  });

  it('locks the main feed toggle but keeps it reorderable', async () => {
    render(Page);
    await screen.findByTestId('insights-sections-editor');

    const feedToggle = screen.getByTestId('insights-section-toggle-insight_feed') as HTMLInputElement;
    expect(feedToggle.checked).toBe(true);
    expect(feedToggle.disabled).toBe(true);
    expect(screen.getByTestId('insights-section-locked-insight_feed')).toBeTruthy();

    // Reordering the locked feed is still allowed.
    await fireEvent.click(screen.getByTestId('insights-section-down-insight_feed'));
    await waitFor(() => {
      expect(updateUserPreferencesMock).toHaveBeenCalled();
    });
    const saved = updateUserPreferencesMock.mock.calls.at(-1)?.[0]?.insight_sections ?? [];
    const feed = saved.find((section) => section.key === 'insight_feed');
    expect(feed?.enabled).toBe(true);
  });

  it('resets to the default layout', async () => {
    render(Page);
    await screen.findByTestId('insights-sections-editor');

    await fireEvent.click(screen.getByTestId('insights-sections-reset'));

    await waitFor(() => {
      expect(updateUserPreferencesMock).toHaveBeenCalledWith({
        insight_sections: DEFAULT_INSIGHT_SECTIONS,
      });
    });
  });
});
