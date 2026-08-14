/**
 * Offline sync orchestrator — push/pull lifecycle (M4.1 Sprint 4).
 */

import { writable, get } from 'svelte/store';
import {
  pullSyncChanges,
  pushSyncChanges,
  type SyncChange,
  type SyncPushResponse,
  type SyncTableName,
} from '$lib/api/sync';
import { ApiError, NetworkError } from '$lib/api/client';
import { fetchEntry } from '$lib/api/entries';
import {
  applyPulledEntry,
  deleteLocalEntry,
  markEntryConflict,
  markEntrySynced,
} from '$lib/stores/entriesOffline';
import { connectivity } from '$lib/stores/connectivity';
import { listPendingChanges, markChangeStatus } from './changeLog';
import { clearClientId, getOrCreateClientId } from './clientId';
import { getOfflineDb } from './db';
import { canUseOfflineSync } from './featureFlag';
import { getSyncMeta, setSyncMeta } from './syncMeta';
import { SYNC_META_KEYS } from './types';
import type { ChangeLogRow, LocalSymptom, LocalTag, OfflineEntityType } from './types';
import { refreshTags } from '$lib/stores/tags';
import { refreshSymptoms } from '$lib/stores/symptoms';

/**
 * Detect retained-client-id + restarted change_log seq collision.
 *
 * When IndexedDB is wiped but `cc_offline_client_id` survives, new outbox
 * rows restart at seq 1 under the old client identity. The server skips
 * them (`seq <= last_applied_seq`) while this client used to ack anyway —
 * silent data loss. Primary mitigation is `getOrCreateClientId()` minting a
 * new identity when the IDB owner/client meta mirror is gone. This probe is
 * defense-in-depth for residual collisions (e.g. unapplied updates to
 * entries that still exist with an older `updated_at`).
 *
 * A 404 alone is NOT a collision signal: legitimate crash-before-ack replay
 * can 404 when the entry was deleted after the original apply — rotating
 * would resurrect it. Only a present-but-stale row proves the skip dropped
 * our push.
 */
async function isStaleClientSeqCollision(toPush: ChangeLogRow[]): Promise<boolean> {
  const entryUpserts = toPush.filter(
    (row) => row.entity_type === 'entry' && row.operation === 'upsert'
  );
  if (entryUpserts.length === 0) return false;
  for (const row of entryUpserts) {
    try {
      const serverEntry = await fetchEntry(row.entity_id);
      const serverAt = new Date(serverEntry.updated_at).getTime();
      const pushedAt = new Date(row.client_ts).getTime();
      if (Number.isFinite(serverAt) && Number.isFinite(pushedAt) && serverAt < pushedAt) {
        return true;
      }
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        // Deleted (or never this id) after a prior apply — keep probing for
        // stale timestamps on other rows; do not rotate on 404 alone.
        continue;
      }
      throw err;
    }
  }
  return false;
}

/**
 * True when the server skipped at least one change for a reason other than
 * idempotent batch replay. Includes the partial-overlap case after an IDB
 * reset: restarted seqs 1..N where only 1..last_applied are skipped and
 * N > last_applied still apply — those skipped rows must not be acked.
 */
function hasNonReplaySkips(response: SyncPushResponse, changeCount: number): boolean {
  return !response.idempotent_replay && changeCount > 0 && response.skipped > 0;
}

export type OfflineSyncBadgeState = 'local' | 'syncing' | 'synced' | 'offline';

export interface SyncOrchestratorState {
  badge: OfflineSyncBadgeState | null;
  pendingCount: number;
  lastPushAt: string | null;
  lastPullAt: string | null;
  conflictNote: string | null;
  syncing: boolean;
}

const initialState: SyncOrchestratorState = {
  badge: null,
  pendingCount: 0,
  lastPushAt: null,
  lastPullAt: null,
  conflictNote: null,
  syncing: false,
};

const store = writable<SyncOrchestratorState>(initialState);

export const syncOrchestrator = { subscribe: store.subscribe };

let syncInFlight: Promise<void> | null = null;
/** Set when scheduleSync runs while a push/pull is already in flight. */
let syncDirty = false;
let initialized = false;
let onlineUnsubscribe: (() => void) | null = null;
/** Test-only: wait on this gate inside `refreshMeta` after `refreshMetaSkip` prior calls. */
let refreshMetaHold: Promise<void> | null = null;
let refreshMetaSkip = 0;

function resetSyncOrchestratorState(): void {
  onlineUnsubscribe?.();
  onlineUnsubscribe = null;
  initialized = false;
  syncInFlight = null;
  syncDirty = false;
  refreshMetaHold = null;
  refreshMetaSkip = 0;
  store.set(initialState);
}

function tableForEntityType(entityType: OfflineEntityType): SyncTableName {
  if (entityType === 'entry') return 'entries';
  if (entityType === 'tag') return 'tags';
  return 'symptoms';
}

async function refreshMeta(): Promise<void> {
  if (refreshMetaHold) {
    if (refreshMetaSkip > 0) {
      refreshMetaSkip -= 1;
    } else {
      const gate = refreshMetaHold;
      refreshMetaHold = null;
      await gate;
    }
  }
  const pending = await listPendingChanges();
  const lastPushAt = await getSyncMeta(SYNC_META_KEYS.lastPushAt);
  const lastPullAt = await getSyncMeta(SYNC_META_KEYS.lastPullAt);
  store.update((s) => ({
    ...s,
    pendingCount: pending.length,
    lastPushAt,
    lastPullAt,
  }));
}

function setBadge(badge: OfflineSyncBadgeState | null): void {
  store.update((s) => ({ ...s, badge }));
}

function setSyncing(syncing: boolean): void {
  store.update((s) => ({ ...s, syncing }));
}

function setConflictNote(note: string | null): void {
  store.update((s) => ({ ...s, conflictNote: note }));
}

async function applyPulledTag(change: SyncChange): Promise<void> {
  const db = getOfflineDb();
  if (change.operation === 'delete') {
    await db.tags.delete(change.id);
    return;
  }
  const data = change.data;
  const row: LocalTag = {
    id: change.id,
    slug: String(data.slug ?? ''),
    name: String(data.name ?? ''),
    category: String(data.category ?? 'custom'),
    icon: data.icon == null ? null : String(data.icon),
    color: data.color == null ? null : String(data.color),
    habit_type: data.habit_type == null ? null : String(data.habit_type),
    target_frequency:
      data.target_frequency == null || data.target_frequency === ''
        ? null
        : Number(data.target_frequency),
    updated_at: change.updated_at,
  };
  await db.tags.put(row);
}

async function applyPulledSymptom(change: SyncChange): Promise<void> {
  const db = getOfflineDb();
  if (change.operation === 'delete') {
    await db.symptoms.delete(change.id);
    return;
  }
  const data = change.data;
  const row: LocalSymptom = {
    id: change.id,
    slug: String(data.slug ?? ''),
    name: String(data.name ?? ''),
    icon: data.icon == null ? null : String(data.icon),
    updated_at: change.updated_at,
  };
  await db.symptoms.put(row);
}

async function applyPullChange(change: SyncChange): Promise<void> {
  if (change.table === 'entries') {
    if (change.operation === 'delete') {
      await deleteLocalEntry(change.id);
      return;
    }
    await applyPulledEntry(change.id, change.data, change.updated_at, 'synced');
    return;
  }

  if (change.table === 'tags') {
    await applyPulledTag(change);
    return;
  }

  if (change.table === 'symptoms') {
    await applyPulledSymptom(change);
  }
}

export async function pullSince(cursor?: string): Promise<void> {
  if (!canUseOfflineSync()) return;

  let since = cursor ?? (await getSyncMeta(SYNC_META_KEYS.lastPullCursor)) ?? undefined;
  let hasMore = true;

  let tagsTouched = false;
  let symptomsTouched = false;

  while (hasMore) {
    const response = await pullSyncChanges({ since, limit: 200 });
    for (const change of response.changes) {
      await applyPullChange(change);
      if (change.table === 'tags') tagsTouched = true;
      if (change.table === 'symptoms') symptomsTouched = true;
    }
    since = response.cursor;
    await setSyncMeta(SYNC_META_KEYS.lastPullCursor, response.cursor);
    hasMore = response.has_more;
  }

  await setSyncMeta(SYNC_META_KEYS.lastPullAt, new Date().toISOString());
  if (tagsTouched) {
    void refreshTags().catch(() => undefined);
  }
  if (symptomsTouched) {
    void refreshSymptoms().catch(() => undefined);
  }
  await refreshMeta();
}

const SYNC_LOCK_NAME = 'correlcore-sync-push';

async function withSyncLock<T>(fn: () => Promise<T>): Promise<T> {
  const locks = typeof navigator !== 'undefined' ? navigator.locks : undefined;
  if (!locks?.request) {
    return fn();
  }
  return locks.request(SYNC_LOCK_NAME, { mode: 'exclusive' }, () => fn());
}

export async function pushPending(): Promise<boolean> {
  if (!canUseOfflineSync()) return false;
  if (typeof navigator !== 'undefined' && !navigator.onLine) return false;

  const pending = await listPendingChanges();
  if (pending.length === 0) return true;

  const latestByEntity = new Map<string, (typeof pending)[number]>();
  for (const row of pending) {
    const prev = latestByEntity.get(row.entity_id);
    if (!prev || (row.seq ?? 0) > (prev.seq ?? 0)) {
      latestByEntity.set(row.entity_id, row);
    }
  }
  const toPush = [...latestByEntity.values()].sort((a, b) => (a.seq ?? 0) - (b.seq ?? 0));

  let clientId = await getOrCreateClientId();
  const changes = toPush.map((row) => ({
    seq: row.seq!,
    id: row.entity_id,
    table: tableForEntityType(row.entity_type),
    operation: row.operation,
    data: row.payload,
    updated_at: row.client_ts,
  }));

  let response = await pushSyncChanges({
    client_id: clientId,
    batch_id: crypto.randomUUID(),
    changes,
  });

  // Skipped rows under a retained client_id after IDB reset must not ack —
  // rotate identity and retry once so the server accepts the restarted seqs.
  // Probe on any non-replay skip (not only fully-skipped batches): when
  // last_applied_seq is small, restarted seqs can partially overlap
  // (1..k skipped, k+1..n applied) and the applied tail used to mask the
  // lost prefix.
  if (hasNonReplaySkips(response, toPush.length) && (await isStaleClientSeqCollision(toPush))) {
    await clearClientId();
    clientId = await getOrCreateClientId();
    response = await pushSyncChanges({
      client_id: clientId,
      batch_id: crypto.randomUUID(),
      changes,
    });
  }

  for (const row of pending) {
    await markChangeStatus(row.seq!, 'acked');
  }

  await setSyncMeta(SYNC_META_KEYS.lastPushAt, new Date().toISOString());

  for (const row of toPush) {
    if (row.entity_type === 'entry') {
      const conflicted = response.conflicts.some((c) => c.entity_id === row.entity_id);
      if (conflicted) {
        await markEntryConflict(row.entity_id);
      } else {
        await markEntrySynced(row.entity_id);
      }
    }
  }

  if (response.conflicts.length > 0) {
    setConflictNote('entry.offline_sync.conflict_note');
  } else {
    setConflictNote(null);
  }

  await refreshMeta();
  return true;
}

export async function syncAll(): Promise<void> {
  if (!canUseOfflineSync()) return;
  if (typeof navigator !== 'undefined' && !navigator.onLine) {
    setBadge('offline');
    await refreshMeta();
    return;
  }

  if (syncInFlight) {
    // A newer local save may have landed; request another drain after this one.
    syncDirty = true;
    await syncInFlight;
    return;
  }

  syncInFlight = withSyncLock(async () => {
    setSyncing(true);
    setBadge('syncing');
    try {
      do {
        syncDirty = false;
        await pushPending();
        await pullSince();
      } while (syncDirty);

      const pending = await listPendingChanges();
      setBadge(pending.length > 0 ? 'local' : 'synced');
      connectivity.markServerReachable(true);
    } catch (err) {
      if (err instanceof NetworkError) {
        setBadge('offline');
        connectivity.markServerReachable(false);
      } else {
        setBadge('local');
      }
      throw err;
    } finally {
      setSyncing(false);
      await refreshMeta();
      syncInFlight = null;
      // A wake-up arrived after the last loop check but before we cleared
      // syncInFlight — schedule a follow-up so the outbox cannot stall.
      if (syncDirty) {
        syncDirty = false;
        scheduleSync();
      }
    }
  });

  await syncInFlight;
}

export function scheduleSync(): void {
  if (!canUseOfflineSync()) return;
  void syncAll().catch(() => {
    // Errors are reflected in orchestrator state; callers need not await.
  });
}

export async function drainOfflineSyncForSessionChange(): Promise<void> {
  // Loop until quiescent: a completing sync may set `syncDirty` after its
  // do-while (e.g. persist/HC `scheduleSync()` during `refreshMeta`) and
  // `finally` starts a follow-up via `scheduleSync()` *after* clearing
  // `syncInFlight`. A single await of the current promise would then
  // `resetSyncOrchestratorState()` while that follow-up is already running,
  // so login()/logout() could swap cookies under an untracked push of the
  // previous account's outbox. Same pattern as entry persist / HC drain.
  while (syncInFlight) {
    const inFlight = syncInFlight;
    try {
      await inFlight;
    } catch {
      // Failed pushes stay pending locally; the session transition must still continue.
    }
    // If we awaited a promise that was replaced mid-wait, keep looping.
    if (syncInFlight === inFlight) {
      break;
    }
  }
  resetSyncOrchestratorState();
}

export function onLocalEntrySaved(): void {
  if (!canUseOfflineSync()) return;
  const online = typeof navigator === 'undefined' ? true : navigator.onLine;
  setBadge(online ? 'local' : 'offline');
  void refreshMeta();
  if (online) scheduleSync();
}

async function handleConnectivityChange(online: boolean): Promise<void> {
  if (!canUseOfflineSync()) return;
  if (online) {
    scheduleSync();
  } else {
    const pending = await listPendingChanges();
    setBadge(pending.length > 0 ? 'offline' : null);
  }
}

function onVisibilityChange(): void {
  if (document.visibilityState === 'visible' && navigator.onLine) {
    scheduleSync();
  }
}

export function initializeSyncOrchestrator(
  subscribeOnline: (listener: (online: boolean) => void) => () => void
): () => void {
  if (initialized || typeof window === 'undefined') {
    return () => undefined;
  }
  initialized = true;

  void refreshMeta();
  onlineUnsubscribe = subscribeOnline((online) => {
    void handleConnectivityChange(online);
  });

  document.addEventListener('visibilitychange', onVisibilityChange);

  if (navigator.onLine) {
    scheduleSync();
  }

  return () => {
    onlineUnsubscribe?.();
    onlineUnsubscribe = null;
    document.removeEventListener('visibilitychange', onVisibilityChange);
    initialized = false;
  };
}

/** Test helper — reset singleton orchestrator hooks. */
export function resetSyncOrchestratorForTests(): void {
  resetSyncOrchestratorState();
}

/**
 * Test-only: the Nth `refreshMeta()` waits on `gate` before reading IDB.
 * `n=3` is the `finally` tail after pushPending + pullSince, so an overlapping
 * `syncAll` can set `syncDirty` after the inner do-while can consume it.
 */
export function _holdNthRefreshMetaForTests(n: number, gate: Promise<void>): void {
  refreshMetaSkip = Math.max(0, n - 1);
  refreshMetaHold = gate;
}

/** Test helper — read orchestrator state synchronously. */
export function peekSyncOrchestrator(): SyncOrchestratorState {
  return get(store);
}
