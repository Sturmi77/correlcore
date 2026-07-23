/**
 * Offline sync orchestrator — push/pull lifecycle (M4.1 Sprint 4).
 */

import { writable, get } from 'svelte/store';
import {
  pullSyncChanges,
  pushSyncChanges,
  type SyncChange,
  type SyncTableName,
} from '$lib/api/sync';
import { NetworkError } from '$lib/api/client';
import {
  applyPulledEntry,
  deleteLocalEntry,
  markEntryConflict,
  markEntrySynced,
} from '$lib/stores/entriesOffline';
import { connectivity } from '$lib/stores/connectivity';
import { listPendingChanges, markChangeStatus } from './changeLog';
import { getOrCreateClientId } from './clientId';
import { getOfflineDb } from './db';
import { canUseOfflineSync } from './featureFlag';
import { getSyncMeta, setSyncMeta } from './syncMeta';
import { SYNC_META_KEYS } from './types';
import type { LocalSymptom, LocalTag, OfflineEntityType } from './types';
import { refreshTags } from '$lib/stores/tags';
import { refreshSymptoms } from '$lib/stores/symptoms';

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

function resetSyncOrchestratorState(): void {
  onlineUnsubscribe?.();
  onlineUnsubscribe = null;
  initialized = false;
  syncInFlight = null;
  syncDirty = false;
  store.set(initialState);
}

function tableForEntityType(entityType: OfflineEntityType): SyncTableName {
  if (entityType === 'entry') return 'entries';
  if (entityType === 'tag') return 'tags';
  return 'symptoms';
}

async function refreshMeta(): Promise<void> {
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

  const clientId = await getOrCreateClientId();
  const batchId = crypto.randomUUID();
  const changes = toPush.map((row) => ({
    seq: row.seq!,
    id: row.entity_id,
    table: tableForEntityType(row.entity_type),
    operation: row.operation,
    data: row.payload,
    updated_at: row.client_ts,
  }));

  const response = await pushSyncChanges({
    client_id: clientId,
    batch_id: batchId,
    changes,
  });

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
  const inFlight = syncInFlight;
  if (inFlight) {
    try {
      await inFlight;
    } catch {
      // Failed pushes stay pending locally; the session transition must still continue.
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

/** Test helper — read orchestrator state synchronously. */
export function peekSyncOrchestrator(): SyncOrchestratorState {
  return get(store);
}
