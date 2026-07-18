import { describe, expect, it } from 'vitest';
import {
  DEV_PHASE_PRESETS,
  devMaturityFromPreset,
  getDevPhaseFixture,
  type DevPhasePresetId,
} from './phaseFixtures';

const phaseIds = Object.keys(DEV_PHASE_PRESETS) as DevPhasePresetId[];

describe('dev phase fixtures', () => {
  it('provides one coherent fixture for each insight maturity phase', () => {
    for (const presetId of phaseIds) {
      const fixture = getDevPhaseFixture({
        presetId,
        entryCount: DEV_PHASE_PRESETS[presetId].defaultEntryCount,
        onboardingCompleted: true,
      });

      expect(fixture.presetId).toBe(presetId);
      expect(fixture.maturity.phase).toBe(presetId);
      expect(fixture.dashboard.entry_count).toBe(fixture.entryCount);
      expect(fixture.entries).toHaveLength(fixture.entryCount);
      expect(fixture.preferences.onboarding_profile_completed).toBe(true);
    }
  });

  it('gates insight and analytics surfaces by phase', () => {
    const collecting = getDevPhaseFixture({
      presetId: 'collecting',
      entryCount: DEV_PHASE_PRESETS.collecting.defaultEntryCount,
      onboardingCompleted: true,
    });
    const robust = getDevPhaseFixture({
      presetId: 'robust',
      entryCount: DEV_PHASE_PRESETS.robust.defaultEntryCount,
      onboardingCompleted: true,
    });

    expect(collecting.insights).toEqual([]);
    expect(collecting.tagCooccurrenceByRange['90d'].pairs).toEqual([]);
    expect(collecting.tagClusters.status).toBe('insufficient_data');
    expect(robust.insights.length).toBeGreaterThan(2);
    expect(robust.tagCooccurrenceByRange['90d'].pairs.length).toBeGreaterThanOrEqual(5);
    expect(robust.tagClusters.status).toBe('ok');
  });

  it('honors entry-count and onboarding overrides', () => {
    const fixture = getDevPhaseFixture({
      presetId: 'provisional',
      entryCount: 18,
      onboardingCompleted: false,
    });

    expect(fixture.maturity).toMatchObject(devMaturityFromPreset('provisional', 18));
    expect(fixture.preferences.onboarding_retro_completed).toBe(false);
    expect(fixture.preferences.onboarding_profile_completed).toBe(false);
    expect(fixture.preferences.onboarding_maturity_intro_seen).toBe(true);
  });
});
