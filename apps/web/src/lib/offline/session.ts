/**
 * Clear offline user data on logout (M4.1 review fix — per-user isolation).
 */

import { CLIENT_ID_STORAGE_KEY } from './clientId';
import { destroyOfflineDatabase, getOfflineDb } from './db';
import { resetSyncOrchestratorForTests } from './syncOrchestrator';
import { SYNC_META_KEYS } from './types';

/** Wipe Dexie data and client identity so the next account starts clean. */
export async function clearOfflineDataForLogout(): Promise<void> {
  if (typeof window === 'undefined') {
    return;
  }
  if (typeof localStorage !== 'undefined') {
    localStorage.removeItem(CLIENT_ID_STORAGE_KEY);
  }
  if (typeof indexedDB !== 'undefined') {
    await destroyOfflineDatabase();
  }
  resetSyncOrchestratorForTests();
}

/** Wipe confirmed stale anonymous-session data before the login UI can read it. */
export async function clearOfflineDataForAnonymousSession(): Promise<void> {
  await clearOfflineDataForLogout();
}

/** Ensure origin-scoped offline data belongs to the authenticated account. */
export async function prepareOfflineDataForAuthenticatedUser(userId: string): Promise<void> {
  if (typeof window === 'undefined' || typeof indexedDB === 'undefined') {
    return;
  }

  const db = getOfflineDb();
  const existingOwner = await db.sync_meta.get(SYNC_META_KEYS.ownerUserId);

  if (existingOwner?.value && existingOwner.value !== userId) {
    await clearOfflineDataForLogout();
  }

  await getOfflineDb().sync_meta.put({ key: SYNC_META_KEYS.ownerUserId, value: userId });
}
