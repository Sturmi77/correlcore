/**
 * Offline sync feature gate — default off until Sprint 4 wires entry UI.
 */

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
