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
import { drainEntryPersistForSessionChange } from './entryPersistLifecycle';
import {
  drainOfflineSyncForSessionChange as drainSyncOrchestratorForSessionChange,
  resetSyncOrchestratorForTests,
} from './syncOrchestrator';
import { SYNC_META_KEYS } from './types';

export async function drainOfflineSyncForSessionChange(): Promise<void> {
  // Offline outbox push first, then entry autosave — both must finish under the
  // current credentials before login/logout swaps Bearer/cookies.
  await drainSyncOrchestratorForSessionChange();
  await drainEntryPersistForSessionChange();
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

function dropRetainedClientId(): void {
  if (typeof localStorage !== 'undefined') {
    localStorage.removeItem(CLIENT_ID_STORAGE_KEY);
  }
}

/** Drop mirrored client identity so the next push mints a fresh server seq space. */
async function dropRetainedClientIdentity(db: CorrelCoreOfflineDB): Promise<void> {
  dropRetainedClientId();
  await db.sync_meta.delete(SYNC_META_KEYS.clientId);
}

/**
 * Ensure offline data belongs to the authenticated account.
 *
 * Same-user sessions keep the currently open DB (including the legacy
 * `correlcore-offline` name used by older clients/tests). Owner mismatches or
 * unknown-owner leftover data on the legacy DB wipe client identity and Dexie
 * state, then open a per-user partition.
 *
 * Ownerless rows already inside `correlcore-offline-<userId>` are treated as
 * mid-session IndexedDB eviction (storage pressure / DevTools clear-IDB): keep
 * pending writes, but drop any retained `cc_offline_client_id` because change_log
 * seqs restarted at 1. Rebound identity + post-#557 "404 does not rotate" would
 * otherwise ack skipped pushes and permanently lose those entries.
 */
export async function prepareOfflineDataForAuthenticatedUser(userId: string): Promise<void> {
  if (typeof window === 'undefined' || typeof indexedDB === 'undefined') {
    return;
  }

  let priorOwner: string | undefined;
  let priorHasData = false;
  let priorDbName = OFFLINE_DB_NAME;
  try {
    const prior = getOfflineDb();
    priorDbName = prior.name;
    priorOwner = (await prior.sync_meta.get(SYNC_META_KEYS.ownerUserId))?.value;
    priorHasData = await hasUnknownOwnerData(prior);
  } catch {
    // Singleton may already be closed from a previous wipe.
  }

  const userPartition = offlineDbNameForUser(userId);
  const priorIsUserPartition = priorDbName === userPartition;

  // Legacy / foreign residue must still be wiped. Ownerless data that already
  // lives in this user's partition is post-eviction same-user state — keep it.
  const shouldWipe =
    (priorOwner != null && priorOwner !== userId) ||
    (priorOwner == null && priorHasData && !priorIsUserPartition);

  if (shouldWipe) {
    dropRetainedClientId();
    await destroyOfflineDatabase(OFFLINE_DB_NAME);
    await destroyOfflineDatabase(userPartition);
    if (priorOwner && priorOwner !== userId) {
      await destroyOfflineDatabase(offlineDbNameForUser(priorOwner));
    }
    resetSyncOrchestratorForTests();
    bindOfflineDbToUser(userId);
  } else if (priorOwner === userId) {
    // Keep the existing DB (legacy or already partitioned) for this owner.
  } else if (priorOwner == null && priorHasData && priorIsUserPartition) {
    // Mid-session eviction while the tab stayed alive: reconnect/online
    // re-runs prepare against the rebound per-user DB with pending writes and
    // no owner marker. Preserve rows; rotate client identity for restarted seqs.
    await dropRetainedClientIdentity(getOfflineDb());
  } else {
    // Fresh empty DB — prefer a per-user partition going forward. The module
    // singleton starts on the empty legacy `correlcore-offline` DB even on a
    // normal reload, so bind the per-user partition first and inspect *it*.
    bindOfflineDbToUser(userId);
    // Only drop the retained origin client_id when the per-user partition is
    // itself fresh, or when it holds ownerless post-eviction writes (seqs
    // restarted). A healthy partition that already has this user's owner marker
    // keeps its identity so reloads no longer mint a new one and crash-before-ack
    // replay detection still works.
    const target = getOfflineDb();
    const targetHasData = await hasUnknownOwnerData(target);
    const targetOwner = (await target.sync_meta.get(SYNC_META_KEYS.ownerUserId))?.value;
    if (!targetHasData || targetOwner == null) {
      await dropRetainedClientIdentity(target);
    }
  }

  await getOfflineDb().sync_meta.put({ key: SYNC_META_KEYS.ownerUserId, value: userId });
}
