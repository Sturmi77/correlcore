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

    const feedToggle = screen.getByTestId(
      'insights-section-toggle-insight_feed'
    ) as HTMLInputElement;
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

  it('reorders sections via move-down control (#847)', async () => {
    render(Page);
    await screen.findByTestId('insights-sections-editor');

    await fireEvent.click(screen.getByTestId('insights-section-down-stage_header'));

    await waitFor(() => {
      expect(updateUserPreferencesMock).toHaveBeenCalledWith({
        insight_sections: [
          { key: 'correlation_matrix', enabled: true },
          { key: 'stage_header', enabled: true },
          { key: 'insight_feed', enabled: true },
          { key: 'lag_heatmap', enabled: true },
          { key: 'dismissed', enabled: true },
          { key: 'symptom_analytics', enabled: true },
          { key: 'tag_groups', enabled: true },
          { key: 'tag_cooccurrence', enabled: true },
        ],
      });
    });

    const rows = screen.getAllByTestId(/^insights-section-row-/);
    expect(rows.map((row) => row.getAttribute('data-testid'))).toEqual([
      'insights-section-row-correlation_matrix',
      'insights-section-row-stage_header',
      'insights-section-row-insight_feed',
      'insights-section-row-lag_heatmap',
      'insights-section-row-dismissed',
      'insights-section-row-symptom_analytics',
      'insights-section-row-tag_groups',
      'insights-section-row-tag_cooccurrence',
    ]);
  });

  it('keeps reorder controls enabled while a save is in flight (#847)', async () => {
    let resolveSave: (() => void) | undefined;
    updateUserPreferencesMock.mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          resolveSave = () =>
            resolve({
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
              insight_sections: [
                { key: 'correlation_matrix', enabled: true },
                { key: 'stage_header', enabled: true },
                { key: 'insight_feed', enabled: true },
                { key: 'lag_heatmap', enabled: true },
                { key: 'dismissed', enabled: true },
                { key: 'symptom_analytics', enabled: true },
                { key: 'tag_groups', enabled: true },
                { key: 'tag_cooccurrence', enabled: true },
              ],
              created_at: '2026-05-16T10:00:00Z',
              updated_at: '2026-05-16T10:00:00Z',
            });
        })
    );

    render(Page);
    await screen.findByTestId('insights-sections-editor');

    await fireEvent.click(screen.getByTestId('insights-section-down-stage_header'));
    const nextMove = screen.getByTestId(
      'insights-section-down-correlation_matrix'
    ) as HTMLButtonElement;
    expect(nextMove.disabled).toBe(false);

    resolveSave?.();
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
