import { render, screen, fireEvent, waitFor } from '@testing-library/svelte';
import { describe, expect, it, vi, beforeEach } from 'vitest';
import Page from './+page.svelte';
import {
  CURRENT_INSIGHT_SECTIONS_VERSION,
  DEFAULT_INSIGHT_SECTIONS,
} from '$lib/utils/insightSections';

vi.mock('svelte-i18n', async () => {
  const { readable } = await import('svelte/store');
  return {
    _: readable((key: string) => key),
    locale: readable('en'),
  };
});

const prefsBase = {
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
  created_at: '2026-05-16T10:00:00Z',
  updated_at: '2026-05-16T10:00:00Z',
};

const { updateUserPreferencesMock } = vi.hoisted(() => ({
  updateUserPreferencesMock: vi.fn(
    async (payload: { insight_sections?: typeof DEFAULT_INSIGHT_SECTIONS }) => ({
      ...prefsBase,
      insight_sections: payload.insight_sections ?? DEFAULT_INSIGHT_SECTIONS,
      insight_sections_version: CURRENT_INSIGHT_SECTIONS_VERSION,
    })
  ),
}));

vi.mock('$lib/api/preferences', () => ({
  fetchUserPreferences: vi.fn(async () => ({
    ...prefsBase,
    insight_sections: DEFAULT_INSIGHT_SECTIONS,
    insight_sections_version: CURRENT_INSIGHT_SECTIONS_VERSION,
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
    // Phase 6 slim default: lag_heatmap starts off.
    expect(toggle.checked).toBe(false);

    await fireEvent.click(toggle);

    await waitFor(() => {
      expect(updateUserPreferencesMock).toHaveBeenCalledWith({
        insight_sections: expect.arrayContaining([
          expect.objectContaining({ key: 'lag_heatmap', enabled: true }),
        ]),
        insight_sections_version: CURRENT_INSIGHT_SECTIONS_VERSION,
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

    // Default order starts stage_header → insight_feed; move stage_header down.
    await fireEvent.click(screen.getByTestId('insights-section-down-stage_header'));

    await waitFor(() => {
      expect(updateUserPreferencesMock).toHaveBeenCalledWith({
        insight_sections: [
          { key: 'insight_feed', enabled: true },
          { key: 'stage_header', enabled: true },
          { key: 'correlation_matrix', enabled: false },
          { key: 'lag_heatmap', enabled: false },
          { key: 'dismissed', enabled: false },
          { key: 'symptom_analytics', enabled: false },
          { key: 'tag_groups', enabled: false },
          { key: 'tag_cooccurrence', enabled: false },
        ],
        insight_sections_version: CURRENT_INSIGHT_SECTIONS_VERSION,
      });
    });

    const rows = screen.getAllByTestId(/^insights-section-row-/);
    expect(rows.map((row) => row.getAttribute('data-testid'))).toEqual([
      'insights-section-row-insight_feed',
      'insights-section-row-stage_header',
      'insights-section-row-correlation_matrix',
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
              ...prefsBase,
              insight_sections: [
                { key: 'insight_feed', enabled: true },
                { key: 'stage_header', enabled: true },
                ...DEFAULT_INSIGHT_SECTIONS.filter(
                  (section) => section.key !== 'stage_header' && section.key !== 'insight_feed'
                ),
              ],
              insight_sections_version: CURRENT_INSIGHT_SECTIONS_VERSION,
            });
        })
    );

    render(Page);
    await screen.findByTestId('insights-sections-editor');

    await fireEvent.click(screen.getByTestId('insights-section-down-stage_header'));
    const nextMove = screen.getByTestId('insights-section-down-insight_feed') as HTMLButtonElement;
    expect(nextMove.disabled).toBe(false);

    resolveSave?.();
  });

  it('does not fire a second PATCH until the in-flight reorder finishes (latest wins)', async () => {
    let resolveFirst: (() => void) | undefined;
    updateUserPreferencesMock.mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          resolveFirst = () =>
            resolve({
              ...prefsBase,
              insight_sections: [
                { key: 'insight_feed', enabled: true },
                { key: 'stage_header', enabled: true },
                ...DEFAULT_INSIGHT_SECTIONS.filter(
                  (section) => section.key !== 'stage_header' && section.key !== 'insight_feed'
                ),
              ],
              insight_sections_version: CURRENT_INSIGHT_SECTIONS_VERSION,
            });
        })
    );

    render(Page);
    await screen.findByTestId('insights-sections-editor');

    await fireEvent.click(screen.getByTestId('insights-section-down-stage_header'));
    await waitFor(() => {
      expect(updateUserPreferencesMock).toHaveBeenCalledTimes(1);
    });

    await fireEvent.click(screen.getByTestId('insights-section-down-stage_header'));
    await Promise.resolve();
    await Promise.resolve();
    expect(updateUserPreferencesMock).toHaveBeenCalledTimes(1);

    resolveFirst?.();

    const latestOrder = [
      'insight_feed',
      'correlation_matrix',
      'stage_header',
      'lag_heatmap',
      'dismissed',
      'symptom_analytics',
      'tag_groups',
      'tag_cooccurrence',
    ];

    await waitFor(() => {
      expect(updateUserPreferencesMock).toHaveBeenCalledTimes(2);
    });
    const lastPayload = updateUserPreferencesMock.mock.calls.at(-1)?.[0]?.insight_sections ?? [];
    expect(lastPayload.map((section: { key: string }) => section.key)).toEqual(latestOrder);

    await waitFor(() => {
      const rows = screen.getAllByTestId(/^insights-section-row-/);
      expect(rows.map((row) => row.getAttribute('data-testid'))).toEqual(
        latestOrder.map((key) => `insights-section-row-${key}`)
      );
    });
  });

  it('resets to the default layout', async () => {
    render(Page);
    await screen.findByTestId('insights-sections-editor');

    await fireEvent.click(screen.getByTestId('insights-sections-reset'));

    await waitFor(() => {
      expect(updateUserPreferencesMock).toHaveBeenCalledWith({
        insight_sections: DEFAULT_INSIGHT_SECTIONS,
        insight_sections_version: CURRENT_INSIGHT_SECTIONS_VERSION,
      });
    });
  });
});
