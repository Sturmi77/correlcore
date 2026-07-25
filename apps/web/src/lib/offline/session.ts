/**
 * Clear offline user data on logout (M4.1 review fix — per-user isolation).
 */

import { CLIENT_ID_STORAGE_KEY } from './clientId';
import {
  OFFLINE_DB_NAME,
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
      // Also drop the legacy unpartitioned DB if present.
      await destroyOfflineDatabase(OFFLINE_DB_NAME);
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

/**
 * Ensure offline data belongs to the authenticated account.
 *
 * Same-user sessions keep the currently open DB (including the legacy
 * `correlcore-offline` name used by older clients/tests). Owner mismatches or
 * unknown-owner leftover data wipe client identity and Dexie state, then open
 * a per-user partition.
 */
export async function prepareOfflineDataForAuthenticatedUser(userId: string): Promise<void> {
  if (typeof window === 'undefined' || typeof indexedDB === 'undefined') {
    return;
  }

  let priorOwner: string | undefined;
  let priorHasData = false;
  try {
    const prior = getOfflineDb();
    priorOwner = (await prior.sync_meta.get(SYNC_META_KEYS.ownerUserId))?.value;
    priorHasData = await hasUnknownOwnerData(prior);
  } catch {
    // Singleton may already be closed from a previous wipe.
  }

  const shouldWipe =
    (priorOwner != null && priorOwner !== userId) || (priorOwner == null && priorHasData);

  if (shouldWipe) {
    if (typeof localStorage !== 'undefined') {
      localStorage.removeItem(CLIENT_ID_STORAGE_KEY);
    }
    await destroyOfflineDatabase(OFFLINE_DB_NAME);
    await destroyOfflineDatabase(offlineDbNameForUser(userId));
    if (priorOwner && priorOwner !== userId) {
      await destroyOfflineDatabase(offlineDbNameForUser(priorOwner));
    }
    resetSyncOrchestratorForTests();
    bindOfflineDbToUser(userId);
  } else if (priorOwner === userId) {
    // Keep the existing DB (legacy or already partitioned) for this owner.
  } else {
    // Fresh empty DB — prefer a per-user partition going forward.
    // Drop any retained origin client_id: IndexedDB can be evicted (or
    // cleared in DevTools) while localStorage survives. Reusing that id
    // with change_log seq restarting at 1 makes the server skip every push
    // (`seq <= last_applied_seq`) while the web client still acks — silent
    // data loss. A new empty DB must mint a new client identity.
    if (typeof localStorage !== 'undefined') {
      localStorage.removeItem(CLIENT_ID_STORAGE_KEY);
    }
    bindOfflineDbToUser(userId);
  }

  await getOfflineDb().sync_meta.put({ key: SYNC_META_KEYS.ownerUserId, value: userId });
}
