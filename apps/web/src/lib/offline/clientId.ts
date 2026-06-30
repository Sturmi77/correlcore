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
 */
export async function getOrCreateClientId(): Promise<string> {
  const existing = readStoredClientId();
  if (existing) {
    if (typeof indexedDB !== 'undefined') {
      const metaValue = await getSyncMeta(SYNC_META_KEYS.clientId);
      if (metaValue !== existing) {
        await setSyncMeta(SYNC_META_KEYS.clientId, existing);
      }
    }
    return existing;
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
