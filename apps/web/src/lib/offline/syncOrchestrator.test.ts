import 'fake-indexeddb/auto';
import { writable } from 'svelte/store';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { appendChange } from './changeLog';
import { resetOfflineDbForTests } from './db';
import { setOfflineSyncEnabled } from './featureFlag';
import {
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

vi.mock('$lib/api/sync', () => ({
  pullSyncChanges: (...args: unknown[]) => pullSyncChanges(...args),
  pushSyncChanges: (...args: unknown[]) => pushSyncChanges(...args),
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
    vi.stubGlobal('navigator', { onLine: true });
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
});
