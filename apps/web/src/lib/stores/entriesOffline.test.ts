import 'fake-indexeddb/auto';
import { beforeEach, describe, expect, it } from 'vitest';
import type { EntryResponse } from '$lib/api/entries';
import { resetOfflineDbForTests } from '$lib/offline/db';
import {
  applyPulledEntry,
  findLocalEntryByDateSlot,
  hydrateServerEntryFromApi,
  saveEntryOffline,
} from './entriesOffline';

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

    await hydrateServerEntryFromApi(apiEntry('server-entry-id'), ['tag-1'], [
      { symptom_id: 'sym-1', intensity: 3 },
    ]);

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
});
