import 'fake-indexeddb/auto';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { EntryResponse } from '$lib/api/entries';
import { listEntries } from '$lib/api/entries';
import { resetOfflineDbForTests } from '$lib/offline/db';
import {
  applyPulledEntry,
  findLocalEntryByDateSlot,
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
    expect(local?.tag_ids).toEqual(['tag-1']);
    expect(local?.symptoms).toEqual({ 'sym-1': 3 });
    expect(local?.sync_state).toBe('synced');
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
      note: '',
      selectedTagIds: [],
      selectedSymptoms: [],
    });

    vi.mocked(listEntries).mockResolvedValue([
      {
        ...apiEntry(saved.entryId),
        cycle_day: null,
        cycle_bleeding_level: null,
      },
    ]);

    const cleared = await clearCycleDataOffline();
    expect(cleared).toBe(1);

    const local = await findLocalEntryByDateSlot('2026-07-13', 'day');
    expect(local?.cycle_day).toBeNull();
    expect(local?.cycle_bleeding_level ?? null).toBeNull();
  });
});
