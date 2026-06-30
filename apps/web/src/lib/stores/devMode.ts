import { derived, writable } from 'svelte/store';

/**
 * devMode store — Issue #165, ADR-0019
 *
 * Persists `dev_mode_enabled` and `dev_force_viz` to localStorage.
 * SSR-safe: localStorage is only accessed inside the browser check.
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

export type DevInsightMaturity = 'collecting' | 'early_patterns' | 'provisional' | 'robust';

export interface DevPhaseState {
  insightMaturity: DevInsightMaturity;
  onboardingCompleted: boolean;
  entryCount: number;
  onboardingPreviewOpen: boolean;
}

const DEFAULT_DEV_PHASE: DevPhaseState = {
  insightMaturity: 'collecting',
  onboardingCompleted: true,
  entryCount: 0,
  onboardingPreviewOpen: false,
};

function readStoredBoolean(key: string): boolean {
  return typeof window !== 'undefined' ? localStorage.getItem(key) === 'true' : false;
}

function writeStoredBoolean(key: string, value: boolean): void {
  if (typeof window !== 'undefined') {
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
    setInsightMaturity(insightMaturity: DevInsightMaturity) {
      update((state) => ({ ...state, insightMaturity }));
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
  devMode.set(readStoredBoolean(DEV_MODE_STORAGE_KEY));
  devForceVisualizationsControl.set(readStoredBoolean(DEV_FORCE_VIZ_STORAGE_KEY));
}
