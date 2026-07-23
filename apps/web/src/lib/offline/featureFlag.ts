/**
 * Offline sync feature gate — default off until enabled for verified users.
 *
 * Exception: when the API is known unreachable after an offline boot, allow
 * the Dexie write/sync path so deferred uploads remain possible without
 * permanently flipping the user preference.
 */

import { get } from 'svelte/store';
import { currentUser } from '$lib/stores/auth';
import { connectivity } from '$lib/stores/connectivity';

export const OFFLINE_SYNC_STORAGE_KEY = 'cc_offline_sync_enabled';

function readStorageOverride(): boolean | null {
  if (typeof localStorage === 'undefined') {
    return null;
  }
  const raw = localStorage.getItem(OFFLINE_SYNC_STORAGE_KEY);
  if (raw === 'true') return true;
  if (raw === 'false') return false;
  return null;
}

/** Whether Dexie-backed offline sync is enabled for this browser session. */
export function isOfflineSyncEnabled(): boolean {
  if (typeof window === 'undefined') {
    return false;
  }

  const override = readStorageOverride();
  if (override !== null) {
    return override;
  }

  const envFlag = import.meta.env.VITE_OFFLINE_SYNC_ENABLED;
  return envFlag === 'true' || envFlag === '1';
}

/** Gate for production entry path — verified users with flag/env/preference on. */
export function canUseOfflineSync(): boolean {
  const user = get(currentUser);
  if (!user?.is_verified) return false;
  if (isOfflineSyncEnabled()) return true;
  // Offline boot / API down: keep deferred sync usable for verified users.
  return get(connectivity).serverReachable === false;
}

/** Dev/test override stored in localStorage. */
export function setOfflineSyncEnabled(enabled: boolean): void {
  if (typeof localStorage === 'undefined') {
    return;
  }
  localStorage.setItem(OFFLINE_SYNC_STORAGE_KEY, String(enabled));
}

export function clearOfflineSyncOverride(): void {
  if (typeof localStorage === 'undefined') {
    return;
  }
  localStorage.removeItem(OFFLINE_SYNC_STORAGE_KEY);
}
