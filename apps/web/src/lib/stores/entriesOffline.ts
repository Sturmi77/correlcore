/**
 * Local-first entry persistence for offline sync (M4.1 Sprint 4).
 */

import type { EntryResponse } from '$lib/api/entries';
import { listEntries } from '$lib/api/entries';
import type { EntrySlot, WorkContext } from '$lib/contracts/apiContract';
import type { SymptomEntry } from '$lib/api/symptoms';
import { ackPendingChangesForEntity, appendChange, listPendingChanges } from '$lib/offline/changeLog';
import { getOfflineDb } from '$lib/offline/db';
import type { LocalEntry, SyncState } from '$lib/offline/types';

export interface EntryFormSnapshot {
  entry_date: string;
  mood_score: number;
  energy: number;
  stress: number;
  slot: EntrySlot;
  cycle_day: number | null;
  cycle_bleeding_level?: import('$lib/api/entries').BleedingLevel | null;
  work_context: WorkContext;
  note: string;
  selectedTagIds: string[];
  selectedSymptoms: SymptomEntry[];
}

function symptomsToMap(symptoms: SymptomEntry[]): Record<string, number> {
  return Object.fromEntries(symptoms.map((s) => [s.symptom_id, s.intensity]));
}

function createEntryId(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  throw new Error('crypto.randomUUID is required for offline entry ids');
}

export function buildSyncEntryPayload(snapshot: EntryFormSnapshot): Record<string, unknown> {
  return {
    entry_date: snapshot.entry_date,
    slot: snapshot.slot,
    mood_score: snapshot.mood_score,
    energy: snapshot.energy,
    stress: snapshot.stress,
    cycle_day: snapshot.cycle_day,
    cycle_bleeding_level: snapshot.cycle_bleeding_level,
    work_context: snapshot.work_context,
    note: snapshot.note ? snapshot.note : null,
    tag_ids: [...snapshot.selectedTagIds],
    symptoms: symptomsToMap(snapshot.selectedSymptoms),
  };
}

export function localEntryToFormFields(entry: LocalEntry): {
  moodScore: number;
  energy: number;
  stress: number;
  selectedSlot: EntrySlot;
  cycleDay: number | null;
  cycleBleedingLevel: import('$lib/api/entries').BleedingLevel | null;
  workContext: WorkContext;
  note: string;
  selectedTagIds: string[];
  selectedSymptoms: SymptomEntry[];
} {
  return {
    moodScore: entry.mood_score,
    energy: entry.energy,
    stress: entry.stress,
    selectedSlot: entry.slot,
    cycleDay: entry.cycle_day,
    cycleBleedingLevel: entry.cycle_bleeding_level ?? null,
    workContext: entry.work_context,
    note: entry.note ?? '',
    selectedTagIds: [...entry.tag_ids],
    selectedSymptoms: Object.entries(entry.symptoms).map(([symptom_id, intensity]) => ({
      symptom_id,
      intensity,
    })),
  };
}

export async function findLocalEntryByDateSlot(
  entryDate: string,
  slot: EntrySlot
): Promise<LocalEntry | undefined> {
  return getOfflineDb()
    .entries.filter((entry) => entry.entry_date === entryDate && entry.slot === slot)
    .first();
}

/** Map a Dexie row to the API shape used by Home and hydration helpers. */
export function localEntryToEntryResponse(entry: LocalEntry, userId = ''): EntryResponse {
  return {
    id: entry.id,
    user_id: userId,
    entry_date: entry.entry_date,
    slot: entry.slot,
    mood_score: entry.mood_score,
    energy: entry.energy,
    stress: entry.stress,
    cycle_day: entry.cycle_day,
    source: 'direct',
    work_context: entry.work_context,
    note: entry.note,
    created_at: entry.updated_at,
    updated_at: entry.updated_at,
  };
}

/**
 * When online, resolve the server-owned id for a date+slot so client creates
 * do not fork a second UUID for an existing server row.
 */
export async function resolveServerEntryIdForDateSlot(
  entryDate: string,
  slot: EntrySlot
): Promise<string | null> {
  if (typeof navigator === 'undefined' || !navigator.onLine) {
    return null;
  }
  try {
    const matches = await listEntries({
      start_date: entryDate,
      end_date: entryDate,
      limit: 5,
    });
    return (
      matches.find((entry) => entry.entry_date === entryDate && entry.slot === slot)?.id ?? null
    );
  } catch {
    return null;
  }
}

/** Keep pending/conflict (or newer) local rows instead of clobbering with stale API data. */
export function shouldPreferLocalEntry(
  local: LocalEntry | undefined,
  serverUpdatedAt: string | undefined
): boolean {
  if (!local) return false;
  if (local.sync_state === 'pending' || local.sync_state === 'conflict') return true;
  if (!serverUpdatedAt) return true;
  return local.updated_at > serverUpdatedAt;
}

async function resolveEntryIdForSave(
  existingEntryId: string | null,
  snapshot: EntryFormSnapshot
): Promise<string> {
  const local = await findLocalEntryByDateSlot(snapshot.entry_date, snapshot.slot);
  const serverId = await resolveServerEntryIdForDateSlot(snapshot.entry_date, snapshot.slot);

  // Prefer the canonical server id when online so slot-merge forks collapse.
  if (serverId) {
    return serverId;
  }
  if (existingEntryId) {
    return existingEntryId;
  }
  if (local) {
    return local.id;
  }
  return createEntryId();
}

export async function getLocalEntry(id: string): Promise<LocalEntry | undefined> {
  return getOfflineDb().entries.get(id);
}

async function deleteStaleEntriesForDateSlot(
  entryId: string,
  entryDate: string,
  slot: EntrySlot
): Promise<void> {
  const stale = await getOfflineDb()
    .entries.filter(
      (entry) => entry.entry_date === entryDate && entry.slot === slot && entry.id !== entryId
    )
    .toArray();
  const db = getOfflineDb();
  for (const row of stale) {
    await db.change_log.where('entity_id').equals(row.id).delete();
    await db.entries.delete(row.id);
  }
}

export async function hydrateServerEntryFromApi(
  entry: EntryResponse,
  tagIds: string[],
  symptoms: SymptomEntry[]
): Promise<void> {
  await applyPulledEntry(
    entry.id,
    {
      entry_date: entry.entry_date,
      slot: entry.slot,
      mood_score: entry.mood_score,
      energy: entry.energy,
      stress: entry.stress,
      cycle_day: entry.cycle_day,
      cycle_bleeding_level: entry.cycle_bleeding_level ?? null,
      work_context: entry.work_context,
      note: entry.note,
      tag_ids: tagIds,
      symptoms: symptomsToMap(symptoms),
    },
    entry.updated_at,
    'synced'
  );
}

export async function saveEntryOffline(
  existingEntryId: string | null,
  snapshot: EntryFormSnapshot
): Promise<{ entryId: string; syncState: SyncState }> {
  if (snapshot.cycle_day !== null && (snapshot.cycle_day < 1 || snapshot.cycle_day > 35)) {
    throw new Error('invalid_cycle_day');
  }

  const now = new Date().toISOString();
  const previousEntryId = existingEntryId;
  const entryId = await resolveEntryIdForSave(existingEntryId, snapshot);
  if (previousEntryId && previousEntryId !== entryId) {
    await ackPendingChangesForEntity(previousEntryId);
    await deleteLocalEntry(previousEntryId);
  }
  const payload = buildSyncEntryPayload(snapshot);
  const syncState: SyncState = 'pending';

  const localEntry: LocalEntry = {
    id: entryId,
    entry_date: snapshot.entry_date,
    slot: snapshot.slot,
    mood_score: snapshot.mood_score,
    energy: snapshot.energy,
    stress: snapshot.stress,
    cycle_day: snapshot.cycle_day,
    cycle_bleeding_level: snapshot.cycle_bleeding_level,
    work_context: snapshot.work_context,
    note: snapshot.note ? snapshot.note : null,
    tag_ids: [...snapshot.selectedTagIds],
    symptoms: symptomsToMap(snapshot.selectedSymptoms),
    updated_at: now,
    sync_state: syncState,
  };

  await getOfflineDb().entries.put(localEntry);

  await ackPendingChangesForEntity(entryId);
  const batchId = crypto.randomUUID();
  await appendChange({
    batch_id: batchId,
    entity_type: 'entry',
    entity_id: entryId,
    operation: 'upsert',
    payload,
    client_ts: now,
  });

  return { entryId, syncState };
}

export async function applyPulledEntry(
  entryId: string,
  data: Record<string, unknown>,
  updatedAt: string,
  syncState: SyncState = 'synced'
): Promise<void> {
  const entryDate = String(data.entry_date);
  const slot = (data.slot as EntrySlot) ?? 'day';
  await deleteStaleEntriesForDateSlot(entryId, entryDate, slot);

  const localEntry: LocalEntry = {
    id: entryId,
    entry_date: String(data.entry_date),
    slot: (data.slot as EntrySlot) ?? 'day',
    mood_score: Number(data.mood_score),
    energy: Number(data.energy),
    stress: Number(data.stress),
    cycle_day: data.cycle_day == null ? null : Number(data.cycle_day),
    cycle_bleeding_level:
      data.cycle_bleeding_level == null || data.cycle_bleeding_level === undefined
        ? null
        : (String(data.cycle_bleeding_level) as import('$lib/api/entries').BleedingLevel),
    work_context: data.work_context as WorkContext,
    note: data.note == null ? null : String(data.note),
    tag_ids: Array.isArray(data.tag_ids) ? data.tag_ids.map(String) : [],
    symptoms:
      data.symptoms && typeof data.symptoms === 'object'
        ? Object.fromEntries(
            Object.entries(data.symptoms as Record<string, number>).map(([k, v]) => [
              String(k),
              Number(v),
            ])
          )
        : {},
    updated_at: updatedAt,
    sync_state: syncState,
  };
  await getOfflineDb().entries.put(localEntry);
}

export async function markEntrySynced(entryId: string): Promise<void> {
  await getOfflineDb().entries.update(entryId, { sync_state: 'synced' });
}

export async function markEntryConflict(entryId: string): Promise<void> {
  await getOfflineDb().entries.update(entryId, { sync_state: 'conflict' });
}

export async function deleteLocalEntry(entryId: string): Promise<void> {
  await getOfflineDb().entries.delete(entryId);
}

function entryHasCycleData(entry: LocalEntry): boolean {
  return (
    entry.cycle_day !== null ||
    (entry.cycle_bleeding_level !== null && entry.cycle_bleeding_level !== undefined)
  );
}

/** Clear cycle SHD fields from IndexedDB and pending outbox payloads (ADR-0033). */
export async function clearCycleDataOffline(): Promise<number> {
  const db = getOfflineDb();
  const entries = await db.entries.toArray();
  const now = new Date().toISOString();
  let cleared = 0;

  for (const entry of entries) {
    if (!entryHasCycleData(entry)) continue;
    cleared += 1;

    await db.entries.update(entry.id, {
      cycle_day: null,
      cycle_bleeding_level: null,
      updated_at: now,
    });

    const pending = await listPendingChanges();
    for (const change of pending) {
      if (change.entity_id !== entry.id || change.operation !== 'upsert') continue;
      const payload = change.payload;
      if (!payload || typeof payload !== 'object' || Array.isArray(payload)) continue;
      await db.change_log.update(change.seq!, {
        payload: {
          ...(payload as Record<string, unknown>),
          cycle_day: null,
          cycle_bleeding_level: null,
        },
      });
    }
  }

  if (typeof navigator !== 'undefined' && navigator.onLine) {
    try {
      const serverEntries = await listEntries({ limit: 500 });
      for (const serverEntry of serverEntries) {
        const local = await db.entries.get(serverEntry.id);
        if (!local) continue;
        await applyPulledEntry(
          serverEntry.id,
          {
            entry_date: serverEntry.entry_date,
            slot: serverEntry.slot,
            mood_score: serverEntry.mood_score,
            energy: serverEntry.energy,
            stress: serverEntry.stress,
            cycle_day: null,
            cycle_bleeding_level: null,
            work_context: serverEntry.work_context,
            note: serverEntry.note,
            tag_ids: local.tag_ids,
            symptoms: local.symptoms,
          },
          serverEntry.updated_at,
          local.sync_state === 'pending' || local.sync_state === 'conflict'
            ? local.sync_state
            : 'synced'
        );
      }
    } catch {
      // Offline pull is best-effort; local scrub above still prevents stale SHD display.
    }
  }

  return cleared;
}
