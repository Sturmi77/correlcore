/**
 * Local-first entry persistence for offline sync (M4.1 Sprint 4).
 */

import type { EntrySlot, WorkContext } from '$lib/contracts/apiContract';
import type { SymptomEntry } from '$lib/api/symptoms';
import { appendChange } from '$lib/offline/changeLog';
import { getOfflineDb } from '$lib/offline/db';
import type { LocalEntry, SyncState } from '$lib/offline/types';

export interface EntryFormSnapshot {
  entry_date: string;
  mood_score: number;
  energy: number;
  stress: number;
  slot: EntrySlot;
  cycle_day: number | null;
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

export async function getLocalEntry(id: string): Promise<LocalEntry | undefined> {
  return getOfflineDb().entries.get(id);
}

export async function saveEntryOffline(
  existingEntryId: string | null,
  snapshot: EntryFormSnapshot
): Promise<{ entryId: string; syncState: SyncState }> {
  if (snapshot.cycle_day !== null && (snapshot.cycle_day < 1 || snapshot.cycle_day > 35)) {
    throw new Error('invalid_cycle_day');
  }

  const now = new Date().toISOString();
  const entryId = existingEntryId ?? createEntryId();
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
    work_context: snapshot.work_context,
    note: snapshot.note ? snapshot.note : null,
    tag_ids: [...snapshot.selectedTagIds],
    symptoms: symptomsToMap(snapshot.selectedSymptoms),
    updated_at: now,
    sync_state: syncState,
  };

  await getOfflineDb().entries.put(localEntry);

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
  const localEntry: LocalEntry = {
    id: entryId,
    entry_date: String(data.entry_date),
    slot: (data.slot as EntrySlot) ?? 'day',
    mood_score: Number(data.mood_score),
    energy: Number(data.energy),
    stress: Number(data.stress),
    cycle_day: data.cycle_day == null ? null : Number(data.cycle_day),
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
