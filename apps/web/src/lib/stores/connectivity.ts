/**
 * Connectivity store — browser online + API reachability.
 *
 * `navigator.onLine` alone is not enough: the device can be "online" while
 * the CorrelCore API is unreachable. Offline boot and the status banner use
 * both signals.
 */

import { get, writable, type Readable } from 'svelte/store';

export interface ConnectivityState {
  /** Mirror of `navigator.onLine` after lifecycle init. */
  browserOnline: boolean;
  /**
   * Latest known API reachability.
   * - `null` — not probed yet
   * - `true` — last /auth/me (or explicit probe) succeeded or returned 401
   * - `false` — transport failure talking to the API
   */
  serverReachable: boolean | null;
}

export type ConnectivityStore = Readable<ConnectivityState> & {
  setBrowserOnline: (online: boolean) => void;
  markServerReachable: (reachable: boolean) => void;
  /** True when the app should behave as offline (no API). */
  isEffectivelyOffline: () => boolean;
  _resetForTests: () => void;
};

function createConnectivityStore(): ConnectivityStore {
  const initial: ConnectivityState = {
    browserOnline: typeof navigator === 'undefined' ? true : navigator.onLine,
    serverReachable: null,
  };
  const { subscribe, update, set } = writable<ConnectivityState>(initial);

  return {
    subscribe,
    setBrowserOnline(online: boolean) {
      update((state) => ({ ...state, browserOnline: online }));
    },
    markServerReachable(reachable: boolean) {
      update((state) => ({ ...state, serverReachable: reachable }));
    },
    isEffectivelyOffline() {
      const state = get({ subscribe });
      return !state.browserOnline || state.serverReachable === false;
    },
    _resetForTests() {
      set({
        browserOnline: typeof navigator === 'undefined' ? true : navigator.onLine,
        serverReachable: null,
      });
    },
  };
}

export const connectivity = createConnectivityStore();

export function isEffectivelyOffline(state: ConnectivityState = get(connectivity)): boolean {
  return !state.browserOnline || state.serverReachable === false;
}
