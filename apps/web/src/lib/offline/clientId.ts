/**
 * Stable offline client identity per browser origin (ADR-0036 §4).
 */

import { getOfflineDb } from './db';
import { getSyncMeta, setSyncMeta } from './syncMeta';
import { SYNC_META_KEYS } from './types';

export const CLIENT_ID_STORAGE_KEY = 'cc_offline_client_id';

function readStoredClientId(): string | null {
  if (typeof localStorage === 'undefined') {
    return null;
  }
  const value = localStorage.getItem(CLIENT_ID_STORAGE_KEY);
  return value && value.length > 0 ? value : null;
}

function writeStoredClientId(clientId: string): void {
  if (typeof localStorage !== 'undefined') {
    localStorage.setItem(CLIENT_ID_STORAGE_KEY, clientId);
  }
}

function createClientId(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  throw new Error('crypto.randomUUID is required for offline client identity');
}

/**
 * Return a stable UUID for this browser origin.
 * Persists in localStorage and mirrors into Dexie `sync_meta`.
 *
 * When IndexedDB is wiped/evicted but `cc_offline_client_id` survives,
 * re-binding that id into an empty DB restarts `change_log` seq at 1 under a
 * server identity that already has `last_applied_seq ≫ 1` — silent skips.
 * If the IDB owner/client meta mirror is gone, mint a new identity instead.
 */
export async function getOrCreateClientId(): Promise<string> {
  const existing = readStoredClientId();
  if (existing) {
    if (typeof indexedDB !== 'undefined') {
      const metaValue = await getSyncMeta(SYNC_META_KEYS.clientId);
      if (metaValue === existing) {
        return existing;
      }
      const owner = await getSyncMeta(SYNC_META_KEYS.ownerUserId);
      // Both mirrors missing ⇒ wiped/empty IDB. Do not restore the retained
      // localStorage client_id into a seq space that restarts at 1.
      if (metaValue == null && owner == null) {
        if (typeof localStorage !== 'undefined') {
          localStorage.removeItem(CLIENT_ID_STORAGE_KEY);
        }
      } else {
        // Self-heal a missing/different mirror while the partition still has
        // an owner (or a mismatched clientId row from an older build).
        await setSyncMeta(SYNC_META_KEYS.clientId, existing);
        return existing;
      }
    } else {
      return existing;
    }
  }

  const clientId = createClientId();
  writeStoredClientId(clientId);

  if (typeof indexedDB !== 'undefined') {
    await setSyncMeta(SYNC_META_KEYS.clientId, clientId);
  }

  return clientId;
}

/** Test helper — read client id without creating Dexie rows when DB is unavailable. */
export function peekClientId(): string | null {
  return readStoredClientId();
}

/** Test helper — clear persisted client identity. */
export async function clearClientId(): Promise<void> {
  if (typeof localStorage !== 'undefined') {
    localStorage.removeItem(CLIENT_ID_STORAGE_KEY);
  }
  if (typeof indexedDB !== 'undefined') {
    await getOfflineDb().sync_meta.delete(SYNC_META_KEYS.clientId);
  }
}
