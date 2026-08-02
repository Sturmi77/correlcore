import 'fake-indexeddb/auto';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { EntryResponse } from '$lib/api/entries';
import { listEntries } from '$lib/api/entries';
import { resetOfflineDbForTests } from '$lib/offline/db';
import { listPendingChanges } from '$lib/offline/changeLog';
import {
  applyPulledEntry,
  findLocalEntryByDateSlot,
  fillLocalSleepAfterHealthConnectImport,
  hydrateServerEntryFromApi,
  localEntryToEntryResponse,
  resolveServerEntryIdForDateSlot,
  saveEntryOffline,
  clearCycleDataOffline,
} from './entriesOffline';

vi.mock('$lib/api/entries', () => ({
  listEntries: vi.fn(),
}));

function apiEntry(id: string): EntryResponse {
  return {
    id,
    user_id: 'user-1',
    entry_date: '2026-07-13',
    slot: 'day',
    mood_score: 4,
    energy: 3,
    stress: 2,
    cycle_day: null,
    sleep_minutes: 420,
    sleep_quality: 4,
    source: 'direct',
    work_context: 'office',
    note: 'server note',
    created_at: '2026-07-13T08:00:00.000Z',
    updated_at: '2026-07-13T08:00:00.000Z',
  };
}

describe('entriesOffline', () => {
  beforeEach(async () => {
    vi.mocked(listEntries).mockReset();
    vi.stubGlobal('navigator', { onLine: true });
    await resetOfflineDbForTests();
  });

  it('reuses an existing local row for the same date+slot on create', async () => {
    const first = await saveEntryOffline(null, {
      entry_date: '2026-07-13',
      mood_score: 3,
      energy: 3,
      stress: 3,
      slot: 'day',
      cycle_day: null,
      work_context: 'office',
      note: '',
      selectedTagIds: [],
      selectedSymptoms: [],
    });

    const second = await saveEntryOffline(null, {
      entry_date: '2026-07-13',
      mood_score: 5,
      energy: 4,
      stress: 1,
      slot: 'day',
      cycle_day: null,
      work_context: 'office',
      note: 'updated',
      selectedTagIds: [],
      selectedSymptoms: [],
    });

    expect(second.entryId).toBe(first.entryId);
    const local = await findLocalEntryByDateSlot('2026-07-13', 'day');
    expect(local?.mood_score).toBe(5);
    expect(local?.note).toBe('updated');
  });

  it('hydrates a server entry and removes stale local duplicates for the slot', async () => {
    await saveEntryOffline(null, {
      entry_date: '2026-07-13',
      mood_score: 2,
      energy: 2,
      stress: 2,
      slot: 'day',
      cycle_day: null,
      work_context: 'office',
      note: 'local only',
      selectedTagIds: [],
      selectedSymptoms: [],
    });

    await hydrateServerEntryFromApi(
      apiEntry('server-entry-id'),
      ['tag-1'],
      [{ symptom_id: 'sym-1', intensity: 3 }]
    );

    const local = await findLocalEntryByDateSlot('2026-07-13', 'day');
    expect(local?.id).toBe('server-entry-id');
    expect(local?.mood_score).toBe(4);
    expect(local?.sleep_minutes).toBe(420);
    expect(local?.sleep_quality).toBe(4);
    expect(local?.tag_ids).toEqual(['tag-1']);
    expect(local?.symptoms).toEqual({ 'sym-1': 3 });
    expect(local?.sync_state).toBe('synced');
  });

  it('preserves sleep fields when applying a pulled entry', async () => {
    await applyPulledEntry(
      'sleep-entry',
      {
        entry_date: '2026-07-13',
        slot: 'day',
        mood_score: 3,
        energy: 3,
        stress: 2,
        sleep_minutes: 390,
        sleep_quality: 5,
        work_context: 'office',
        note: null,
        tag_ids: [],
        symptoms: {},
      },
      '2026-07-13T09:00:00.000Z',
      'synced'
    );

    const local = await findLocalEntryByDateSlot('2026-07-13', 'day');
    expect(local?.sleep_minutes).toBe(390);
    expect(local?.sleep_quality).toBe(5);
  });

  it('preserves existing sleep when a pull omits sleep keys', async () => {
    await applyPulledEntry(
      'sleep-entry',
      {
        entry_date: '2026-07-13',
        slot: 'day',
        mood_score: 3,
        energy: 3,
        stress: 2,
        sleep_minutes: 420,
        sleep_quality: 4,
        work_context: 'office',
        note: null,
        tag_ids: [],
        symptoms: {},
      },
      '2026-07-13T09:00:00.000Z',
      'synced'
    );

    await applyPulledEntry(
      'sleep-entry',
      {
        entry_date: '2026-07-13',
        slot: 'day',
        mood_score: 4,
        energy: 3,
        stress: 2,
        cycle_day: null,
        cycle_bleeding_level: null,
        work_context: 'office',
        note: null,
        tag_ids: [],
        symptoms: {},
      },
      '2026-07-13T10:00:00.000Z',
      'synced'
    );

    const local = await findLocalEntryByDateSlot('2026-07-13', 'day');
    expect(local?.mood_score).toBe(4);
    expect(local?.sleep_minutes).toBe(420);
    expect(local?.sleep_quality).toBe(4);
  });

  it('clears sleep when a pull sends explicit null sleep keys', async () => {
    await applyPulledEntry(
      'sleep-entry',
      {
        entry_date: '2026-07-13',
        slot: 'day',
        mood_score: 3,
        energy: 3,
        stress: 2,
        sleep_minutes: 420,
        sleep_quality: 4,
        work_context: 'office',
        note: null,
        tag_ids: [],
        symptoms: {},
      },
      '2026-07-13T09:00:00.000Z',
      'synced'
    );

    await applyPulledEntry(
      'sleep-entry',
      {
        entry_date: '2026-07-13',
        slot: 'day',
        mood_score: 3,
        energy: 3,
        stress: 2,
        sleep_minutes: null,
        sleep_quality: null,
        work_context: 'office',
        note: null,
        tag_ids: [],
        symptoms: {},
      },
      '2026-07-13T10:00:00.000Z',
      'synced'
    );

    const local = await findLocalEntryByDateSlot('2026-07-13', 'day');
    expect(local?.sleep_minutes).toBeNull();
    expect(local?.sleep_quality).toBeNull();
  });

  it('dedupes stale rows when applying a pulled entry', async () => {
    await applyPulledEntry(
      'client-a',
      {
        entry_date: '2026-07-13',
        slot: 'day',
        mood_score: 2,
        energy: 2,
        stress: 2,
        work_context: 'office',
        note: null,
        tag_ids: [],
        symptoms: {},
      },
      '2026-07-13T07:00:00.000Z',
      'pending'
    );
    await applyPulledEntry(
      'server-b',
      {
        entry_date: '2026-07-13',
        slot: 'day',
        mood_score: 4,
        energy: 3,
        stress: 2,
        work_context: 'office',
        note: null,
        tag_ids: [],
        symptoms: {},
      },
      '2026-07-13T08:00:00.000Z',
      'synced'
    );

    const local = await findLocalEntryByDateSlot('2026-07-13', 'day');
    expect(local?.id).toBe('server-b');
  });

  it('resolves the server id for an existing date+slot when online', async () => {
    vi.mocked(listEntries).mockResolvedValue([apiEntry('server-entry-id')]);

    await expect(resolveServerEntryIdForDateSlot('2026-07-13', 'day')).resolves.toBe(
      'server-entry-id'
    );
  });

  it('reuses the server id on save when online and the API already has the slot', async () => {
    vi.mocked(listEntries).mockResolvedValue([apiEntry('server-entry-id')]);

    const result = await saveEntryOffline(null, {
      entry_date: '2026-07-13',
      mood_score: 5,
      energy: 4,
      stress: 1,
      slot: 'day',
      cycle_day: null,
      work_context: 'office',
      note: 'updated',
      selectedTagIds: [],
      selectedSymptoms: [],
    });

    expect(result.entryId).toBe('server-entry-id');
    const local = await findLocalEntryByDateSlot('2026-07-13', 'day');
    expect(local?.id).toBe('server-entry-id');
    expect(local?.mood_score).toBe(5);
  });

  it('remaps a client UUID to the server id when the slot already exists online', async () => {
    vi.mocked(listEntries).mockResolvedValue([apiEntry('server-entry-id')]);

    const result = await saveEntryOffline('client-fork-id', {
      entry_date: '2026-07-13',
      mood_score: 5,
      energy: 4,
      stress: 1,
      slot: 'day',
      cycle_day: null,
      work_context: 'office',
      note: 'remapped',
      selectedTagIds: [],
      selectedSymptoms: [],
    });

    expect(result.entryId).toBe('server-entry-id');
    const local = await findLocalEntryByDateSlot('2026-07-13', 'day');
    expect(local?.id).toBe('server-entry-id');
    expect(local?.note).toBe('remapped');
  });

  it('prefers pending local rows over older server timestamps', async () => {
    const { shouldPreferLocalEntry } = await import('./entriesOffline');
    expect(
      shouldPreferLocalEntry(
        {
          id: 'local-1',
          entry_date: '2026-07-13',
          slot: 'day',
          mood_score: 5,
          energy: 4,
          stress: 1,
          cycle_day: null,
          work_context: 'office',
          note: 'pending',
          tag_ids: [],
          symptoms: {},
          updated_at: '2026-07-13T09:00:00.000Z',
          sync_state: 'pending',
        },
        '2026-07-13T08:00:00.000Z'
      )
    ).toBe(true);
    expect(
      shouldPreferLocalEntry(
        {
          id: 'local-1',
          entry_date: '2026-07-13',
          slot: 'day',
          mood_score: 3,
          energy: 3,
          stress: 3,
          cycle_day: null,
          work_context: 'office',
          note: null,
          tag_ids: [],
          symptoms: {},
          updated_at: '2026-07-13T07:00:00.000Z',
          sync_state: 'synced',
        },
        '2026-07-13T08:00:00.000Z'
      )
    ).toBe(false);
  });

  it('maps local entries to the API response shape for Home', () => {
    const mapped = localEntryToEntryResponse({
      id: 'local-1',
      entry_date: '2026-07-13',
      slot: 'day',
      mood_score: 4,
      energy: 3,
      stress: 2,
      cycle_day: null,
      sleep_minutes: 480,
      sleep_quality: 3,
      work_context: 'office',
      note: 'hello',
      tag_ids: [],
      symptoms: {},
      updated_at: '2026-07-13T08:00:00.000Z',
      sync_state: 'pending',
    });

    expect(mapped.id).toBe('local-1');
    expect(mapped.entry_date).toBe('2026-07-13');
    expect(mapped.mood_score).toBe(4);
    expect(mapped.sleep_minutes).toBe(480);
    expect(mapped.sleep_quality).toBe(3);
  });

  it('clears cycle fields from local entries and pending outbox payloads', async () => {
    const saved = await saveEntryOffline(null, {
      entry_date: '2026-07-13',
      mood_score: 3,
      energy: 3,
      stress: 3,
      slot: 'day',
      cycle_day: 12,
      cycle_bleeding_level: 'medium',
      work_context: 'office',
      note: 'keep me',
      selectedTagIds: [],
      selectedSymptoms: [],
    });

    vi.mocked(listEntries).mockResolvedValue([
      {
        ...apiEntry(saved.entryId),
        mood_score: 1,
        energy: 1,
        stress: 5,
        note: 'stale server',
        cycle_day: null,
        cycle_bleeding_level: null,
      },
    ]);

    const cleared = await clearCycleDataOffline();
    expect(cleared).toBe(1);

    const local = await findLocalEntryByDateSlot('2026-07-13', 'day');
    expect(local?.cycle_day).toBeNull();
    expect(local?.cycle_bleeding_level ?? null).toBeNull();
    // Pending local body fields must survive the post-delete server hydrate.
    expect(local?.mood_score).toBe(3);
    expect(local?.energy).toBe(3);
    expect(local?.stress).toBe(3);
    expect(local?.note).toBe('keep me');
    expect(local?.sync_state).toBe('pending');

    const pending = await listPendingChanges();
    const upsert = pending.find((row) => row.entity_id === saved.entryId);
    expect(upsert?.payload).toMatchObject({
      mood_score: 3,
      note: 'keep me',
      cycle_day: null,
      cycle_bleeding_level: null,
    });
  });

  it('does not clobber pending non-cycle edits when clearing cycle data', async () => {
    const saved = await saveEntryOffline(null, {
      entry_date: '2026-07-13',
      mood_score: 5,
      energy: 4,
      stress: 1,
      slot: 'day',
      cycle_day: null,
      work_context: 'homeoffice',
      note: 'pending note',
      selectedTagIds: [],
      selectedSymptoms: [],
    });

    // A different local row still has SHD so clearCycleDataOffline runs the
    // online server hydrate path (which previously overwrote *all* locals).
    await applyPulledEntry(
      'other-entry',
      {
        entry_date: '2026-07-12',
        slot: 'day',
        mood_score: 2,
        energy: 2,
        stress: 2,
        cycle_day: 8,
        cycle_bleeding_level: 'light',
        work_context: 'office',
        note: null,
        tag_ids: [],
        symptoms: {},
      },
      '2026-07-12T08:00:00.000Z',
      'synced'
    );

    vi.mocked(listEntries).mockResolvedValue([
      {
        ...apiEntry(saved.entryId),
        mood_score: 1,
        energy: 1,
        stress: 5,
        work_context: 'office',
        note: 'stale server',
        cycle_day: null,
        cycle_bleeding_level: null,
      },
      {
        ...apiEntry('other-entry'),
        entry_date: '2026-07-12',
        mood_score: 2,
        energy: 2,
        stress: 2,
        cycle_day: null,
        cycle_bleeding_level: null,
        note: null,
        updated_at: '2026-07-12T09:00:00.000Z',
      },
    ]);

    const cleared = await clearCycleDataOffline();
    expect(cleared).toBe(1);

    const pendingLocal = await findLocalEntryByDateSlot('2026-07-13', 'day');
    expect(pendingLocal?.mood_score).toBe(5);
    expect(pendingLocal?.note).toBe('pending note');
    expect(pendingLocal?.work_context).toBe('homeoffice');
    expect(pendingLocal?.sync_state).toBe('pending');

    const syncedOther = await findLocalEntryByDateSlot('2026-07-12', 'day');
    expect(syncedOther?.cycle_day).toBeNull();
    expect(syncedOther?.cycle_bleeding_level ?? null).toBeNull();
  });

  it('preserves sleep when clearing cycle data rehydrates synced rows', async () => {
    await applyPulledEntry(
      'sleep-cycle-entry',
      {
        entry_date: '2026-07-13',
        slot: 'day',
        mood_score: 4,
        energy: 3,
        stress: 2,
        cycle_day: 10,
        cycle_bleeding_level: 'light',
        sleep_minutes: 450,
        sleep_quality: 5,
        work_context: 'office',
        note: 'keep sleep',
        tag_ids: [],
        symptoms: {},
      },
      '2026-07-13T08:00:00.000Z',
      'synced'
    );

    vi.mocked(listEntries).mockResolvedValue([
      {
        ...apiEntry('sleep-cycle-entry'),
        mood_score: 4,
        energy: 3,
        stress: 2,
        cycle_day: null,
        cycle_bleeding_level: null,
        sleep_minutes: 450,
        sleep_quality: 5,
        note: 'keep sleep',
        updated_at: '2026-07-13T09:00:00.000Z',
      },
    ]);

    const cleared = await clearCycleDataOffline();
    expect(cleared).toBe(1);

    const local = await findLocalEntryByDateSlot('2026-07-13', 'day');
    expect(local?.cycle_day).toBeNull();
    expect(local?.cycle_bleeding_level ?? null).toBeNull();
    expect(local?.sleep_minutes).toBe(450);
    expect(local?.sleep_quality).toBe(5);
    expect(local?.note).toBe('keep sleep');
    expect(local?.sync_state).toBe('synced');
  });

  it('fills local null sleep after Health Connect import so offline edits cannot wipe it', async () => {
    await applyPulledEntry(
      'hc-entry',
      {
        entry_date: '2026-07-13',
        slot: 'day',
        mood_score: 3,
        energy: 3,
        stress: 2,
        cycle_day: null,
        sleep_minutes: null,
        sleep_quality: null,
        work_context: 'office',
        note: null,
        tag_ids: [],
        symptoms: {},
      },
      '2026-07-13T08:00:00.000Z',
      'synced'
    );

    vi.mocked(listEntries).mockResolvedValue([
      {
        ...apiEntry('hc-entry'),
        sleep_minutes: 430,
        sleep_quality: null,
        updated_at: '2026-07-13T10:00:00.000Z',
      },
    ]);

    const filled = await fillLocalSleepAfterHealthConnectImport([
      { entry_date: '2026-07-13', sleep_minutes: 430 },
    ]);
    expect(filled).toBe(1);

    const local = await findLocalEntryByDateSlot('2026-07-13', 'day');
    expect(local?.sleep_minutes).toBe(430);
    expect(local?.mood_score).toBe(3);
  });

  it('patches pending outbox null sleep after Health Connect import', async () => {
    const saved = await saveEntryOffline(null, {
      entry_date: '2026-07-13',
      mood_score: 4,
      energy: 3,
      stress: 2,
      slot: 'day',
      cycle_day: null,
      sleep_minutes: null,
      sleep_quality: null,
      work_context: 'office',
      note: 'mood only',
      selectedTagIds: [],
      selectedSymptoms: [],
    });

    vi.mocked(listEntries).mockResolvedValue([
      {
        ...apiEntry(saved.entryId),
        mood_score: 3,
        sleep_minutes: 410,
        sleep_quality: null,
        note: null,
        updated_at: '2026-07-13T09:00:00.000Z',
      },
    ]);

    const filled = await fillLocalSleepAfterHealthConnectImport([
      { entry_date: '2026-07-13', sleep_minutes: 410 },
    ]);
    expect(filled).toBe(1);

    const local = await findLocalEntryByDateSlot('2026-07-13', 'day');
    expect(local?.sleep_minutes).toBe(410);
    expect(local?.mood_score).toBe(4);
    expect(local?.sync_state).toBe('pending');

    const pending = await listPendingChanges();
    const upsert = pending.find((row) => row.entity_id === saved.entryId);
    expect(upsert?.payload).toMatchObject({
      mood_score: 4,
      note: 'mood only',
      sleep_minutes: 410,
    });
  });

  it('does not overwrite local sleep or mismatched server values after HC import', async () => {
    await applyPulledEntry(
      'manual-entry',
      {
        entry_date: '2026-07-13',
        slot: 'day',
        mood_score: 3,
        energy: 3,
        stress: 2,
        cycle_day: null,
        sleep_minutes: 480,
        sleep_quality: 4,
        work_context: 'office',
        note: null,
        tag_ids: [],
        symptoms: {},
      },
      '2026-07-13T08:00:00.000Z',
      'synced'
    );

    // Server kept the manual value (HC skipped); imported minutes differ.
    vi.mocked(listEntries).mockResolvedValue([
      {
        ...apiEntry('manual-entry'),
        sleep_minutes: 480,
        sleep_quality: 4,
      },
    ]);

    const filled = await fillLocalSleepAfterHealthConnectImport([
      { entry_date: '2026-07-13', sleep_minutes: 999 },
    ]);
    expect(filled).toBe(0);

    const local = await findLocalEntryByDateSlot('2026-07-13', 'day');
    expect(local?.sleep_minutes).toBe(480);
  });
});
