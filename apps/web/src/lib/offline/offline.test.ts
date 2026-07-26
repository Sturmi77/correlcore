import 'fake-indexeddb/auto';
import { beforeEach, describe, expect, it } from 'vitest';
import { appendChange, getLastAppliedSeq, listPendingChanges } from './changeLog';
import { CLIENT_ID_STORAGE_KEY, getOrCreateClientId } from './clientId';
import { bindOfflineDbToUser, getOfflineDb, resetOfflineDbForTests } from './db';
import { isOfflineSyncEnabled } from './featureFlag';
import { applyPulledEntry } from '$lib/stores/entriesOffline';
import {
  clearOfflineDataForAnonymousSession,
  prepareOfflineDataForAuthenticatedUser,
} from './session';
import { getSyncMeta, setSyncMeta } from './syncMeta';
import { SYNC_META_KEYS } from './types';
import type { LocalEntry } from './types';

function sampleEntry(id: string): LocalEntry {
  return {
    id,
    entry_date: '2026-06-30',
    slot: 'day',
    mood_score: 3,
    energy: 3,
    stress: 3,
    cycle_day: null,
    work_context: 'office',
    note: 'hello',
    tag_ids: [],
    symptoms: {},
    updated_at: '2026-06-30T12:00:00.000Z',
    sync_state: 'pending',
  };
}

describe('offline Dexie foundation', () => {
  beforeEach(async () => {
    localStorage.clear();
    await resetOfflineDbForTests();
  });

  it('persists entries round-trip', async () => {
    const db = getOfflineDb();
    const entry = sampleEntry('e1');
    await db.entries.put(entry);
    const loaded = await db.entries.get('e1');
    expect(loaded).toEqual(entry);
  });

  it('assigns monotonic change_log seq', async () => {
    const base = {
      batch_id: 'batch-1',
      entity_type: 'entry' as const,
      client_ts: '2026-06-30T12:00:00.000Z',
    };
    const seqA = await appendChange({
      ...base,
      entity_id: 'e1',
      operation: 'upsert',
      payload: { id: 'e1' },
    });
    const seqB = await appendChange({
      ...base,
      entity_id: 'e2',
      operation: 'upsert',
      payload: { id: 'e2' },
    });
    expect(seqB).toBeGreaterThan(seqA);
    const pending = await listPendingChanges();
    expect(pending).toHaveLength(2);
  });

  it('reports highest change_log seq via getLastAppliedSeq', async () => {
    const base = {
      batch_id: 'batch-1',
      entity_type: 'entry' as const,
      client_ts: '2026-06-30T12:00:00.000Z',
    };
    expect(await getLastAppliedSeq()).toBe(0);
    const seq = await appendChange({
      ...base,
      entity_id: 'e1',
      operation: 'upsert',
      payload: {},
    });
    expect(await getLastAppliedSeq()).toBe(seq);
  });

  it('stores sync cursor in sync_meta', async () => {
    await setSyncMeta(SYNC_META_KEYS.lastPullCursor, 'cursor-abc');
    expect(await getSyncMeta(SYNC_META_KEYS.lastPullCursor)).toBe('cursor-abc');
  });

  it('returns stable client id', async () => {
    const first = await getOrCreateClientId();
    const second = await getOrCreateClientId();
    expect(first).toBe(second);
    expect(first).toMatch(
      /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i
    );
  });

  it('defaults offline sync feature flag to off', () => {
    expect(isOfflineSyncEnabled()).toBe(false);
  });

  it('keeps offline data when the authenticated user is unchanged', async () => {
    const db = getOfflineDb();
    await setSyncMeta(SYNC_META_KEYS.ownerUserId, 'usr_1');
    await db.entries.put(sampleEntry('e1'));

    await prepareOfflineDataForAuthenticatedUser('usr_1');

    expect(await db.entries.get('e1')).toEqual(sampleEntry('e1'));
    expect(await getSyncMeta(SYNC_META_KEYS.ownerUserId)).toBe('usr_1');
  });

  it('wipes offline data and client identity when the authenticated user changes', async () => {
    const db = getOfflineDb();
    await setSyncMeta(SYNC_META_KEYS.ownerUserId, 'usr_1');
    await db.entries.put(sampleEntry('e1'));
    await appendChange({
      batch_id: 'batch-1',
      entity_type: 'entry',
      entity_id: 'e1',
      operation: 'upsert',
      payload: { id: 'e1' },
      client_ts: '2026-06-30T12:00:00.000Z',
    });
    const previousClientId = await getOrCreateClientId();
    expect(localStorage.getItem(CLIENT_ID_STORAGE_KEY)).toBe(previousClientId);

    await prepareOfflineDataForAuthenticatedUser('usr_2');

    const freshDb = getOfflineDb();
    expect(await freshDb.entries.count()).toBe(0);
    expect(await freshDb.change_log.count()).toBe(0);
    expect(await getSyncMeta(SYNC_META_KEYS.clientId)).toBeNull();
    expect(localStorage.getItem(CLIENT_ID_STORAGE_KEY)).toBeNull();
    expect(await getSyncMeta(SYNC_META_KEYS.ownerUserId)).toBe('usr_2');
  });

  it('drops retained client id when binding a fresh empty offline DB', async () => {
    // IndexedDB wiped / never opened, but origin localStorage still holds a
    // prior sync client_id (eviction, DevTools clear of IDB only, etc.).
    const staleClientId = '11111111-1111-4111-8111-111111111111';
    localStorage.setItem(CLIENT_ID_STORAGE_KEY, staleClientId);
    expect(await getSyncMeta(SYNC_META_KEYS.ownerUserId)).toBeNull();

    await prepareOfflineDataForAuthenticatedUser('usr_fresh');

    expect(localStorage.getItem(CLIENT_ID_STORAGE_KEY)).toBeNull();
    expect(await getSyncMeta(SYNC_META_KEYS.ownerUserId)).toBe('usr_fresh');
    const nextClientId = await getOrCreateClientId();
    expect(nextClientId).not.toBe(staleClientId);
  });

  it('mints a new client id when IDB meta is gone but localStorage retains one', async () => {
    // Mid-session IndexedDB eviction: no owner/client mirror, but the origin
    // localStorage key survived. Re-binding the old id would restart seqs
    // under a server identity that already has last_applied_seq ≫ 1.
    const staleClientId = '22222222-2222-4222-8222-222222222222';
    localStorage.setItem(CLIENT_ID_STORAGE_KEY, staleClientId);
    expect(await getSyncMeta(SYNC_META_KEYS.clientId)).toBeNull();
    expect(await getSyncMeta(SYNC_META_KEYS.ownerUserId)).toBeNull();

    const nextClientId = await getOrCreateClientId();

    expect(nextClientId).not.toBe(staleClientId);
    expect(localStorage.getItem(CLIENT_ID_STORAGE_KEY)).toBe(nextClientId);
    expect(await getSyncMeta(SYNC_META_KEYS.clientId)).toBe(nextClientId);
  });

  it('keeps ownerless per-user partition writes after mid-session eviction + reconnect', async () => {
    // Eviction cleared sync_meta (and tables) while the tab stayed on the
    // per-user DB. Post-eviction offline saves have no owner marker; prepare
    // used to wipe them as "unknown-owner" before push — permanent loss.
    await prepareOfflineDataForAuthenticatedUser('usr_evict');
    const staleClientId = await getOrCreateClientId();
    const db = getOfflineDb();
    await Promise.all([db.entries.clear(), db.change_log.clear(), db.sync_meta.clear()]);
    expect(db.name).toBe('correlcore-offline-usr_evict');
    expect(localStorage.getItem(CLIENT_ID_STORAGE_KEY)).toBe(staleClientId);

    await db.entries.put(sampleEntry('post-evict'));
    await appendChange({
      batch_id: 'batch-evict',
      entity_type: 'entry',
      entity_id: 'post-evict',
      operation: 'upsert',
      payload: { id: 'post-evict' },
      client_ts: '2026-06-30T12:00:00.000Z',
    });

    await prepareOfflineDataForAuthenticatedUser('usr_evict');

    const kept = getOfflineDb();
    expect(await kept.entries.get('post-evict')).toEqual(sampleEntry('post-evict'));
    expect(await listPendingChanges()).toHaveLength(1);
    expect(await getSyncMeta(SYNC_META_KEYS.ownerUserId)).toBe('usr_evict');
    expect(localStorage.getItem(CLIENT_ID_STORAGE_KEY)).toBeNull();
    expect(await getSyncMeta(SYNC_META_KEYS.clientId)).toBeNull();
    const nextClientId = await getOrCreateClientId();
    expect(nextClientId).not.toBe(staleClientId);
  });

  it('drops retained client id when reloading into ownerless per-user partition data', async () => {
    // Page reload after eviction: JS singleton starts on empty legacy DB, then
    // bind opens the per-user partition that already holds post-eviction writes.
    // Keeping the retained client_id would skip restarted seqs; post-#557 a
    // probe 404 no longer rotates — silent ack/loss.
    const userDb = bindOfflineDbToUser('usr_reload');
    const staleClientId = '33333333-3333-4333-8333-333333333333';
    localStorage.setItem(CLIENT_ID_STORAGE_KEY, staleClientId);
    await userDb.entries.put(sampleEntry('reload-evict'));
    await appendChange({
      batch_id: 'batch-reload',
      entity_type: 'entry',
      entity_id: 'reload-evict',
      operation: 'upsert',
      payload: { id: 'reload-evict' },
      client_ts: '2026-06-30T12:00:00.000Z',
    });
    expect(await getSyncMeta(SYNC_META_KEYS.ownerUserId)).toBeNull();

    // Simulate reload: singleton returns to empty legacy without deleting the
    // per-user partition that still holds the pending entry.
    await resetOfflineDbForTests();
    expect(getOfflineDb().name).toBe('correlcore-offline');

    await prepareOfflineDataForAuthenticatedUser('usr_reload');

    const recovered = getOfflineDb();
    expect(recovered.name).toBe('correlcore-offline-usr_reload');
    expect(await recovered.entries.get('reload-evict')).toEqual(sampleEntry('reload-evict'));
    expect(await listPendingChanges()).toHaveLength(1);
    expect(await getSyncMeta(SYNC_META_KEYS.ownerUserId)).toBe('usr_reload');
    expect(localStorage.getItem(CLIENT_ID_STORAGE_KEY)).toBeNull();
    const nextClientId = await getOrCreateClientId();
    expect(nextClientId).not.toBe(staleClientId);
  });

  it('wipes unknown-owner migrated offline data before assigning it to the current user', async () => {
    const db = getOfflineDb();
    await db.entries.put(sampleEntry('legacy-entry'));
    await appendChange({
      batch_id: 'legacy-batch',
      entity_type: 'entry',
      entity_id: 'legacy-entry',
      operation: 'upsert',
      payload: { id: 'legacy-entry' },
      client_ts: '2026-06-30T12:00:00.000Z',
    });
    const legacyClientId = await getOrCreateClientId();
    expect(await getSyncMeta(SYNC_META_KEYS.ownerUserId)).toBeNull();
    expect(localStorage.getItem(CLIENT_ID_STORAGE_KEY)).toBe(legacyClientId);

    await prepareOfflineDataForAuthenticatedUser('usr_2');

    const freshDb = getOfflineDb();
    expect(await freshDb.entries.count()).toBe(0);
    expect(await freshDb.change_log.count()).toBe(0);
    expect(await getSyncMeta(SYNC_META_KEYS.clientId)).toBeNull();
    expect(localStorage.getItem(CLIENT_ID_STORAGE_KEY)).toBeNull();
    expect(await getSyncMeta(SYNC_META_KEYS.ownerUserId)).toBe('usr_2');
  });

  it('wipes offline data and client identity for a confirmed anonymous session', async () => {
    const db = getOfflineDb();
    await setSyncMeta(SYNC_META_KEYS.ownerUserId, 'usr_1');
    await db.entries.put(sampleEntry('e1'));
    const previousClientId = await getOrCreateClientId();
    expect(localStorage.getItem(CLIENT_ID_STORAGE_KEY)).toBe(previousClientId);

    await clearOfflineDataForAnonymousSession();

    const freshDb = getOfflineDb();
    expect(await freshDb.entries.count()).toBe(0);
    expect(await getSyncMeta(SYNC_META_KEYS.ownerUserId)).toBeNull();
    expect(localStorage.getItem(CLIENT_ID_STORAGE_KEY)).toBeNull();
  });

  it('removes stale duplicate entries and their pending outbox rows on pull hydrate', async () => {
    const db = getOfflineDb();
    await db.entries.put(sampleEntry('canonical'));
    await db.entries.put({ ...sampleEntry('stale-client'), id: 'stale-client' });
    await appendChange({
      batch_id: 'batch-stale',
      entity_type: 'entry',
      entity_id: 'stale-client',
      operation: 'upsert',
      payload: { id: 'stale-client' },
      client_ts: '2026-06-30T12:00:00.000Z',
    });

    await applyPulledEntry(
      'canonical',
      {
        entry_date: '2026-06-30',
        slot: 'day',
        mood_score: 4,
        energy: 3,
        stress: 2,
        cycle_day: null,
        work_context: 'office',
        note: null,
        tag_ids: [],
        symptoms: {},
      },
      '2026-06-30T13:00:00.000Z',
      'synced'
    );

    expect(await db.entries.get('stale-client')).toBeUndefined();
    expect(await db.entries.get('canonical')).toBeDefined();
    expect(await listPendingChanges()).toHaveLength(0);
  });
});
