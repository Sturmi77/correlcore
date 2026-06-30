import 'fake-indexeddb/auto';
import { beforeEach, describe, expect, it } from 'vitest';
import { appendChange, getLastAppliedSeq, listPendingChanges } from './changeLog';
import { CLIENT_ID_STORAGE_KEY, getOrCreateClientId } from './clientId';
import { getOfflineDb, resetOfflineDbForTests } from './db';
import { isOfflineSyncEnabled } from './featureFlag';
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
});
