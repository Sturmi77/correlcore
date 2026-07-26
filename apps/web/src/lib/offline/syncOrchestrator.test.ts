import 'fake-indexeddb/auto';
import { writable } from 'svelte/store';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiError } from '$lib/api/client';
import { appendChange, listPendingChanges } from './changeLog';
import { CLIENT_ID_STORAGE_KEY, getOrCreateClientId, peekClientId } from './clientId';
import { resetOfflineDbForTests } from './db';
import { setOfflineSyncEnabled } from './featureFlag';
import {
  drainOfflineSyncForSessionChange,
  peekSyncOrchestrator,
  pullSince,
  pushPending,
  resetSyncOrchestratorForTests,
  syncAll,
} from './syncOrchestrator';
import { getSyncMeta, setSyncMeta } from './syncMeta';
import { SYNC_META_KEYS } from './types';

const pullSyncChanges = vi.fn();
const pushSyncChanges = vi.fn();
const fetchEntry = vi.fn();

vi.mock('$lib/api/sync', () => ({
  pullSyncChanges: (...args: unknown[]) => pullSyncChanges(...args),
  pushSyncChanges: (...args: unknown[]) => pushSyncChanges(...args),
}));

vi.mock('$lib/api/entries', () => ({
  fetchEntry: (...args: unknown[]) => fetchEntry(...args),
}));

vi.mock('$lib/stores/auth', () => ({
  currentUser: writable({
    id: '00000000-0000-4000-8000-000000000099',
    email: 'sync@test.example',
    display_name: 'Sync User',
    is_verified: true,
  }),
}));

describe('syncOrchestrator', () => {
  beforeEach(async () => {
    localStorage.clear();
    resetSyncOrchestratorForTests();
    await resetOfflineDbForTests();
    setOfflineSyncEnabled(true);
    pullSyncChanges.mockReset();
    pushSyncChanges.mockReset();
    fetchEntry.mockReset();
    vi.stubGlobal('navigator', { onLine: true });
  });

  it('pushes only the latest pending change per entity', async () => {
    const first = await appendChange({
      batch_id: 'batch-1',
      entity_type: 'entry',
      entity_id: 'e1',
      operation: 'upsert',
      payload: { mood_score: 2 },
      client_ts: '2026-06-30T12:00:00.000Z',
    });
    await appendChange({
      batch_id: 'batch-2',
      entity_type: 'entry',
      entity_id: 'e1',
      operation: 'upsert',
      payload: { mood_score: 4 },
      client_ts: '2026-06-30T12:01:00.000Z',
    });

    pushSyncChanges.mockResolvedValue({
      cursor: 'cursor-dedupe',
      applied: 1,
      skipped: 0,
      conflicts: [],
      idempotent_replay: false,
    });

    await pushPending();

    expect(pushSyncChanges).toHaveBeenCalledOnce();
    const body = pushSyncChanges.mock.calls[0]?.[0];
    expect(body.changes).toHaveLength(1);
    expect(body.changes[0].seq).toBeGreaterThan(first);
    expect(body.changes[0].data).toEqual({ mood_score: 4 });
    expect(peekSyncOrchestrator().pendingCount).toBe(0);
  });

  it('pushes pending changes and marks them acked', async () => {
    const seq = await appendChange({
      batch_id: 'batch-1',
      entity_type: 'entry',
      entity_id: 'e1',
      operation: 'upsert',
      payload: { entry_date: '2026-06-30', slot: 'day' },
      client_ts: '2026-06-30T12:00:00.000Z',
    });

    pushSyncChanges.mockResolvedValue({
      cursor: 'cursor-1',
      applied: 1,
      skipped: 0,
      conflicts: [],
      idempotent_replay: false,
    });
    pullSyncChanges.mockResolvedValue({
      cursor: 'cursor-1',
      changes: [],
      has_more: false,
      server_time: '2026-06-30T12:01:00.000Z',
    });

    await syncAll();

    expect(pushSyncChanges).toHaveBeenCalledOnce();
    expect(pullSyncChanges).toHaveBeenCalled();
    expect(peekSyncOrchestrator().pendingCount).toBe(0);
    expect(peekSyncOrchestrator().badge).toBe('synced');
    expect(await getSyncMeta(SYNC_META_KEYS.lastPushAt)).not.toBeNull();
    expect(seq).toBeGreaterThan(0);
  });

  it('does not overwrite the pull cursor after push', async () => {
    await setSyncMeta(SYNC_META_KEYS.lastPullCursor, 'cursor-before-push');
    await appendChange({
      batch_id: 'batch-1',
      entity_type: 'entry',
      entity_id: 'e1',
      operation: 'upsert',
      payload: {},
      client_ts: '2026-06-30T12:00:00.000Z',
    });
    pushSyncChanges.mockResolvedValue({
      cursor: 'cursor-after-push',
      applied: 1,
      skipped: 0,
      conflicts: [],
      idempotent_replay: false,
    });
    await pushPending();
    expect(await getSyncMeta(SYNC_META_KEYS.lastPullCursor)).toBe('cursor-before-push');
  });

  it('stores conflict note without throwing', async () => {
    await appendChange({
      batch_id: 'batch-1',
      entity_type: 'entry',
      entity_id: 'e1',
      operation: 'upsert',
      payload: { entry_date: '2026-06-30' },
      client_ts: '2026-06-30T12:00:00.000Z',
    });

    pushSyncChanges.mockResolvedValue({
      cursor: 'cursor-2',
      applied: 1,
      skipped: 0,
      conflicts: [
        {
          entity_id: 'e1',
          entity_type: 'entry',
          field_name: 'mood_score',
          client_ts: '2026-06-30T12:00:00.000Z',
          server_ts: '2026-06-30T12:05:00.000Z',
          winner: 'server',
        },
      ],
      idempotent_replay: false,
    });
    pullSyncChanges.mockResolvedValue({
      cursor: 'cursor-2',
      changes: [],
      has_more: false,
      server_time: '2026-06-30T12:05:00.000Z',
    });

    await pushPending();
    await pullSince();

    expect(peekSyncOrchestrator().conflictNote).toBe('entry.offline_sync.conflict_note');
  });

  it('skips push while offline', async () => {
    vi.stubGlobal('navigator', { onLine: false });
    await appendChange({
      batch_id: 'batch-1',
      entity_type: 'entry',
      entity_id: 'e1',
      operation: 'upsert',
      payload: {},
      client_ts: '2026-06-30T12:00:00.000Z',
    });

    const pushed = await pushPending();
    expect(pushed).toBe(false);
    expect(pushSyncChanges).not.toHaveBeenCalled();
  });

  it('rotates client id and retries when all-skipped push hides a missing entry', async () => {
    const staleClientId = await getOrCreateClientId();
    await appendChange({
      batch_id: 'batch-1',
      entity_type: 'entry',
      entity_id: 'missing-on-server',
      operation: 'upsert',
      payload: { entry_date: '2026-06-30', slot: 'day', mood_score: 4 },
      client_ts: '2026-06-30T12:00:00.000Z',
    });

    pushSyncChanges
      .mockResolvedValueOnce({
        cursor: 'cursor-skip',
        applied: 0,
        skipped: 1,
        conflicts: [],
        idempotent_replay: false,
      })
      .mockResolvedValueOnce({
        cursor: 'cursor-applied',
        applied: 1,
        skipped: 0,
        conflicts: [],
        idempotent_replay: false,
      });
    fetchEntry.mockRejectedValue(new ApiError(404, 'Not Found', '/entries/missing-on-server'));

    await pushPending();

    expect(pushSyncChanges).toHaveBeenCalledTimes(2);
    expect(fetchEntry).toHaveBeenCalledWith('missing-on-server');
    const retryClientId = pushSyncChanges.mock.calls[1]?.[0]?.client_id as string;
    expect(retryClientId).toBeTruthy();
    expect(retryClientId).not.toBe(staleClientId);
    expect(peekClientId()).toBe(retryClientId);
    expect(localStorage.getItem(CLIENT_ID_STORAGE_KEY)).toBe(retryClientId);
    expect(await listPendingChanges()).toHaveLength(0);
  });

  it('acks all-skipped push when the entry already exists (crash-before-ack)', async () => {
    const clientId = await getOrCreateClientId();
    await appendChange({
      batch_id: 'batch-1',
      entity_type: 'entry',
      entity_id: 'already-on-server',
      operation: 'upsert',
      payload: { entry_date: '2026-06-30', slot: 'day' },
      client_ts: '2026-06-30T12:00:00.000Z',
    });

    pushSyncChanges.mockResolvedValue({
      cursor: 'cursor-skip',
      applied: 0,
      skipped: 1,
      conflicts: [],
      idempotent_replay: false,
    });
    fetchEntry.mockResolvedValue({
      id: 'already-on-server',
      entry_date: '2026-06-30',
      slot: 'day',
      mood_score: 3,
      energy: 3,
      stress: 3,
      cycle_day: null,
      work_context: 'office',
      note: null,
      created_at: '2026-06-30T12:00:00.000Z',
      updated_at: '2026-06-30T12:00:00.000Z',
    });

    await pushPending();

    expect(pushSyncChanges).toHaveBeenCalledOnce();
    expect(pushSyncChanges.mock.calls[0]?.[0]?.client_id).toBe(clientId);
    expect(fetchEntry).toHaveBeenCalledWith('already-on-server');
    expect(peekClientId()).toBe(clientId);
    expect(await listPendingChanges()).toHaveLength(0);
  });

  it('rotates when an all-skipped entry exists but is stale (unapplied update)', async () => {
    // The entry was created under the retained id before the IDB reset, so it
    // exists on the server — but our restarted-seq UPDATE was skipped and never
    // applied, leaving the server `updated_at` older than what we pushed.
    // Existence alone would wrongly ack this and lose the update (P1).
    const staleClientId = await getOrCreateClientId();
    await appendChange({
      batch_id: 'batch-1',
      entity_type: 'entry',
      entity_id: 'stale-on-server',
      operation: 'upsert',
      payload: { entry_date: '2026-06-30', slot: 'day', mood_score: 5 },
      client_ts: '2026-06-30T12:00:00.000Z',
    });

    pushSyncChanges
      .mockResolvedValueOnce({
        cursor: 'cursor-skip',
        applied: 0,
        skipped: 1,
        conflicts: [],
        idempotent_replay: false,
      })
      .mockResolvedValueOnce({
        cursor: 'cursor-applied',
        applied: 1,
        skipped: 0,
        conflicts: [],
        idempotent_replay: false,
      });
    fetchEntry.mockResolvedValue({
      id: 'stale-on-server',
      entry_date: '2026-06-30',
      slot: 'day',
      mood_score: 2,
      energy: 3,
      stress: 3,
      cycle_day: null,
      work_context: 'office',
      note: null,
      created_at: '2026-06-30T11:00:00.000Z',
      updated_at: '2026-06-30T11:00:00.000Z',
    });

    await pushPending();

    expect(pushSyncChanges).toHaveBeenCalledTimes(2);
    expect(fetchEntry).toHaveBeenCalledWith('stale-on-server');
    const retryClientId = pushSyncChanges.mock.calls[1]?.[0]?.client_id as string;
    expect(retryClientId).toBeTruthy();
    expect(retryClientId).not.toBe(staleClientId);
    expect(peekClientId()).toBe(retryClientId);
    expect(await listPendingChanges()).toHaveLength(0);
  });

  it('applies pull deltas to local entries', async () => {
    await setSyncMeta(SYNC_META_KEYS.lastPullCursor, 'cursor-old');
    pullSyncChanges.mockResolvedValue({
      cursor: 'cursor-new',
      changes: [
        {
          seq: 1,
          id: 'server-entry-1',
          table: 'entries',
          operation: 'upsert',
          data: {
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
          updated_at: '2026-06-30T13:00:00.000Z',
        },
      ],
      has_more: false,
      server_time: '2026-06-30T13:00:00.000Z',
    });

    await pullSince();

    const { getOfflineDb } = await import('./db');
    const entry = await getOfflineDb().entries.get('server-entry-1');
    expect(entry?.mood_score).toBe(4);
    expect(await getSyncMeta(SYNC_META_KEYS.lastPullCursor)).toBe('cursor-new');
  });

  it('drains an in-flight sync before a session-cookie change proceeds', async () => {
    await appendChange({
      batch_id: 'batch-1',
      entity_type: 'entry',
      entity_id: 'e1',
      operation: 'upsert',
      payload: { entry_date: '2026-06-30', slot: 'day' },
      client_ts: '2026-06-30T12:00:00.000Z',
    });

    let releasePush!: () => void;
    pushSyncChanges.mockReturnValue(
      new Promise((resolve) => {
        releasePush = () =>
          resolve({
            cursor: 'cursor-1',
            applied: 1,
            skipped: 0,
            conflicts: [],
            idempotent_replay: false,
          });
      })
    );
    pullSyncChanges.mockResolvedValue({
      cursor: 'cursor-1',
      changes: [],
      has_more: false,
      server_time: '2026-06-30T12:01:00.000Z',
    });

    const syncPromise = syncAll();
    await vi.waitFor(() => {
      expect(pushSyncChanges).toHaveBeenCalledOnce();
    });

    let drained = false;
    const drainPromise = drainOfflineSyncForSessionChange().then(() => {
      drained = true;
    });
    await Promise.resolve();
    expect(drained).toBe(false);

    releasePush();
    await drainPromise;
    await syncPromise;

    expect(drained).toBe(true);
    expect(peekSyncOrchestrator()).toEqual({
      badge: null,
      pendingCount: 0,
      lastPushAt: null,
      lastPullAt: null,
      conflictNote: null,
      syncing: false,
    });
  });

  it('re-drains the outbox when a save lands during an in-flight sync', async () => {
    await appendChange({
      batch_id: 'batch-1',
      entity_type: 'entry',
      entity_id: 'e1',
      operation: 'upsert',
      payload: { mood_score: 2 },
      client_ts: '2026-06-30T12:00:00.000Z',
    });

    let releaseFirstPush!: () => void;
    pushSyncChanges.mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          releaseFirstPush = () =>
            resolve({
              cursor: 'cursor-1',
              applied: 1,
              skipped: 0,
              conflicts: [],
              idempotent_replay: false,
            });
        })
    );
    pushSyncChanges.mockResolvedValue({
      cursor: 'cursor-2',
      applied: 1,
      skipped: 0,
      conflicts: [],
      idempotent_replay: false,
    });
    pullSyncChanges.mockResolvedValue({
      cursor: 'cursor-1',
      changes: [],
      has_more: false,
      server_time: '2026-06-30T12:01:00.000Z',
    });

    const first = syncAll();
    await vi.waitFor(() => {
      expect(pushSyncChanges).toHaveBeenCalledOnce();
    });

    await appendChange({
      batch_id: 'batch-2',
      entity_type: 'entry',
      entity_id: 'e1',
      operation: 'upsert',
      payload: { mood_score: 5 },
      client_ts: '2026-06-30T12:02:00.000Z',
    });
    const second = syncAll();

    releaseFirstPush();
    await first;
    await second;
    await vi.waitFor(() => {
      expect(pushSyncChanges.mock.calls.length).toBeGreaterThanOrEqual(2);
    });

    const lastBody = pushSyncChanges.mock.calls.at(-1)?.[0];
    expect(lastBody.changes).toHaveLength(1);
    expect(lastBody.changes[0].data).toEqual({ mood_score: 5 });
    expect(peekSyncOrchestrator().pendingCount).toBe(0);
  });
});
