import { derived, writable } from 'svelte/store';
import { DEV_PHASE_PRESETS, type DevPhasePresetId } from '$lib/dev/phaseFixtures';

/**
 * devMode store — Issue #165, ADR-0019, #589
 *
 * Persists `dev_mode_enabled` and `dev_force_viz` to localStorage.
 * SSR-safe: localStorage is only accessed inside the browser check.
 *
 * **Production:** Client developer mode is intentionally available in production
 * builds (Cloud + selfhost). Unlock via 7× tap on the Settings version string;
 * Force Visualizations and phase mocks are not gated by `import.meta.env.DEV`.
 * Backend `/dev` diagnostics remain separate (`DEV_VIEW_ENABLED` on the API).
 *
 * Usage:
 *   import { devMode } from '$lib/stores/devMode';
 *   $devMode                  // boolean
 *   $devForceVisualizations   // boolean, only true when dev mode is active
 *   devMode.set(true)         // activate
 *   devMode.toggle()          // flip
 */

export const DEV_MODE_STORAGE_KEY = 'dev_mode_enabled';
export const DEV_FORCE_VIZ_STORAGE_KEY = 'dev_force_viz';

export type DevInsightMaturity = DevPhasePresetId;

export interface DevPhaseState {
  presetId: DevPhasePresetId;
  onboardingCompleted: boolean;
  entryCount: number;
  onboardingPreviewOpen: boolean;
}

const DEFAULT_DEV_PHASE: DevPhaseState = {
  presetId: 'collecting',
  onboardingCompleted: true,
  entryCount: DEV_PHASE_PRESETS.collecting.defaultEntryCount,
  onboardingPreviewOpen: false,
};

function readStoredBoolean(key: string): boolean {
  return typeof window !== 'undefined' ? localStorage.getItem(key) === 'true' : false;
}

function writeStoredBoolean(key: string, value: boolean): void {
  if (typeof window !== 'undefined') {
    // storage-exempt: generic helper, callers pass DEV_*_STORAGE_KEY only
    localStorage.setItem(key, String(value));
  }
}

function createDevModeStore() {
  const initial = readStoredBoolean(DEV_MODE_STORAGE_KEY);

  const { subscribe, set, update } = writable<boolean>(initial);

  return {
    subscribe,
    set(value: boolean) {
      writeStoredBoolean(DEV_MODE_STORAGE_KEY, value);
      if (!value) {
        forceVisualizations.set(false);
        devPhase.reset();
      }
      set(value);
    },
    toggle() {
      update((current) => {
        const next = !current;
        writeStoredBoolean(DEV_MODE_STORAGE_KEY, next);
        if (!next) {
          forceVisualizations.set(false);
          devPhase.reset();
        }
        return next;
      });
    },
  };
}

function createForceVisualizationsStore() {
  const initial = readStoredBoolean(DEV_FORCE_VIZ_STORAGE_KEY);
  const { subscribe, set } = writable<boolean>(initial);

  return {
    subscribe,
    set(value: boolean) {
      writeStoredBoolean(DEV_FORCE_VIZ_STORAGE_KEY, value);
      set(value);
    },
  };
}

const forceVisualizations = createForceVisualizationsStore();

function createDevPhaseStore() {
  const { subscribe, set, update } = writable<DevPhaseState>({ ...DEFAULT_DEV_PHASE });
  return {
    subscribe,
    setPreset(presetId: DevPhasePresetId) {
      update((state) => ({
        ...state,
        presetId,
        entryCount: DEV_PHASE_PRESETS[presetId].defaultEntryCount,
      }));
    },
    setInsightMaturity(insightMaturity: DevInsightMaturity) {
      update((state) => ({
        ...state,
        presetId: insightMaturity,
        entryCount: DEV_PHASE_PRESETS[insightMaturity].defaultEntryCount,
      }));
    },
    setOnboardingCompleted(onboardingCompleted: boolean) {
      update((state) => ({ ...state, onboardingCompleted }));
    },
    setEntryCount(entryCount: number) {
      update((state) => ({ ...state, entryCount: Math.max(0, Math.min(200, entryCount)) }));
    },
    setOnboardingPreviewOpen(onboardingPreviewOpen: boolean) {
      update((state) => ({ ...state, onboardingPreviewOpen }));
    },
    reset() {
      set({ ...DEFAULT_DEV_PHASE });
    },
  };
}

export const devPhase = createDevPhaseStore();

export const devMode = createDevModeStore();
export const devModeEnabled = devMode;
export const devForceVisualizations = derived(
  [devMode, forceVisualizations],
  ([$devMode, $forceVisualizations]) => $devMode && $forceVisualizations
);
export const devForceVisualizationsControl = forceVisualizations;

/** Re-read persisted dev flags after init scripts or external storage writes. */
export function syncDevModeFromStorage(): void {
  if (typeof window === 'undefined') return;
  const devEnabled = readStoredBoolean(DEV_MODE_STORAGE_KEY);
  devMode.set(devEnabled);
  const forceVizStored = readStoredBoolean(DEV_FORCE_VIZ_STORAGE_KEY);
  const forceViz = devEnabled && forceVizStored;
  devForceVisualizationsControl.set(forceViz);
  if (!devEnabled && forceVizStored) {
    writeStoredBoolean(DEV_FORCE_VIZ_STORAGE_KEY, false);
  }
}
