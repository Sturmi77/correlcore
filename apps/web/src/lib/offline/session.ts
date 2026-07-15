/**
 * Clear offline user data on logout (M4.1 review fix — per-user isolation).
 */

import { CLIENT_ID_STORAGE_KEY } from './clientId';
import {
  bindOfflineDbToUser,
  destroyOfflineDatabase,
  getOfflineDb,
  offlineDbNameForUser,
  type CorrelCoreOfflineDB,
} from './db';
import {
  drainOfflineSyncForSessionChange as drainSyncOrchestratorForSessionChange,
  resetSyncOrchestratorForTests,
} from './syncOrchestrator';
import { SYNC_META_KEYS } from './types';

export async function drainOfflineSyncForSessionChange(): Promise<void> {
  await drainSyncOrchestratorForSessionChange();
}

/** Wipe Dexie data and client identity so the next account starts clean. */
export async function clearOfflineDataForLogout(userId?: string | null): Promise<void> {
  if (typeof window === 'undefined') {
    return;
  }
  if (typeof localStorage !== 'undefined') {
    localStorage.removeItem(CLIENT_ID_STORAGE_KEY);
  }
  if (typeof indexedDB !== 'undefined') {
    if (userId) {
      await destroyOfflineDatabase(offlineDbNameForUser(userId));
    } else {
      await destroyOfflineDatabase();
    }
  }
  resetSyncOrchestratorForTests();
}

/** Wipe confirmed stale anonymous-session data before the login UI can read it. */
export async function clearOfflineDataForAnonymousSession(): Promise<void> {
  await clearOfflineDataForLogout();
}

async function hasUnknownOwnerData(db: CorrelCoreOfflineDB): Promise<boolean> {
  const [entryCount, changeCount, metaCount] = await Promise.all([
    db.entries.count(),
    db.change_log.count(),
    db.sync_meta.count(),
  ]);
  return entryCount > 0 || changeCount > 0 || metaCount > 0;
}

/** Ensure offline data belongs to the authenticated account (per-user Dexie). */
export async function prepareOfflineDataForAuthenticatedUser(userId: string): Promise<void> {
  if (typeof window === 'undefined' || typeof indexedDB === 'undefined') {
    return;
  }

  const db = bindOfflineDbToUser(userId);
  const existingOwner = await db.sync_meta.get(SYNC_META_KEYS.ownerUserId);

  if (
    (existingOwner?.value && existingOwner.value !== userId) ||
    (!existingOwner?.value && (await hasUnknownOwnerData(db)))
  ) {
    await clearOfflineDataForLogout(userId);
  }

  await getOfflineDb(userId).sync_meta.put({ key: SYNC_META_KEYS.ownerUserId, value: userId });
}
