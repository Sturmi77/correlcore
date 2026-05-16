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
      }
      set(value);
    },
    toggle() {
      update((current) => {
        const next = !current;
        writeStoredBoolean(DEV_MODE_STORAGE_KEY, next);
        if (!next) {
          forceVisualizations.set(false);
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

export const devMode = createDevModeStore();
export const devModeEnabled = devMode;
export const devForceVisualizations = derived(
  [devMode, forceVisualizations],
  ([$devMode, $forceVisualizations]) => $devMode && $forceVisualizations
);
export const devForceVisualizationsControl = forceVisualizations;
