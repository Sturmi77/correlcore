import 'fake-indexeddb/auto';
import { beforeEach, describe, expect, it } from 'vitest';
import { appendChange, getLastAppliedSeq, listPendingChanges } from './changeLog';
import { getOrCreateClientId } from './clientId';
import { getOfflineDb, resetOfflineDbForTests } from './db';
import { isOfflineSyncEnabled } from './featureFlag';
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
});
