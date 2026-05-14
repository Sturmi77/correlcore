import { writable } from 'svelte/store';

/**
 * devMode store — Issue #165, ADR-0019
 *
 * Persists `dev_mode_enabled` to localStorage.
 * SSR-safe: localStorage is only accessed inside the browser check.
 *
 * Usage:
 *   import { devMode } from '$lib/stores/devMode';
 *   $devMode          // boolean
 *   devMode.set(true) // activate
 *   devMode.toggle()  // flip
 */

const STORAGE_KEY = 'dev_mode_enabled';

function createDevModeStore() {
  // SSR-safe initial value
  const initial =
    typeof window !== 'undefined'
      ? localStorage.getItem(STORAGE_KEY) === 'true'
      : false;

  const { subscribe, set, update } = writable<boolean>(initial);

  return {
    subscribe,
    set(value: boolean) {
      if (typeof window !== 'undefined') {
        localStorage.setItem(STORAGE_KEY, String(value));
      }
      set(value);
    },
    toggle() {
      update((current) => {
        const next = !current;
        if (typeof window !== 'undefined') {
          localStorage.setItem(STORAGE_KEY, String(next));
        }
        return next;
      });
    }
  };
}

export const devMode = createDevModeStore();
