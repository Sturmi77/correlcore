/**
 * Local-first entry persistence for offline sync (M4.1 Sprint 4).
 */

import type { EntryResponse } from '$lib/api/entries';
import { listEntries } from '$lib/api/entries';
import type { EntrySlot, WorkContext } from '$lib/contracts/apiContract';
import type { SymptomEntry } from '$lib/api/symptoms';
import {
  ackPendingChangesForEntity,
  appendChange,
  listPendingChanges,
} from '$lib/offline/changeLog';
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
  sleep_minutes?: number | null;
  sleep_quality?: number | null;
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
    sleep_minutes: snapshot.sleep_minutes ?? null,
    sleep_quality: snapshot.sleep_quality ?? null,
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
  sleepMinutes: number | null;
  sleepQuality: number | null;
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
    sleepMinutes: entry.sleep_minutes ?? null,
    sleepQuality: entry.sleep_quality ?? null,
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
    cycle_bleeding_level: entry.cycle_bleeding_level ?? null,
    sleep_minutes: entry.sleep_minutes ?? null,
    sleep_quality: entry.sleep_quality ?? null,
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
      sleep_minutes: entry.sleep_minutes ?? null,
      sleep_quality: entry.sleep_quality ?? null,
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
    sleep_minutes: snapshot.sleep_minutes ?? null,
    sleep_quality: snapshot.sleep_quality ?? null,
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

function sleepFieldFromPull(
  data: Record<string, unknown>,
  key: 'sleep_minutes' | 'sleep_quality',
  existing: number | null | undefined
): number | null {
  // Presence-aware: partial callers (e.g. clearCycleDataOffline) may omit sleep
  // keys. Treating omitted as null would wipe IDB sleep and later push nulls
  // to the server after an offline/API-down edit. Explicit null still clears.
  if (!(key in data)) {
    return existing ?? null;
  }
  const value = data[key];
  return value == null ? null : Number(value);
}

export async function applyPulledEntry(
  entryId: string,
  data: Record<string, unknown>,
  updatedAt: string,
  syncState: SyncState = 'synced'
): Promise<void> {
  const entryDate = String(data.entry_date);
  const slot = (data.slot as EntrySlot) ?? 'day';
  const existing = await getOfflineDb().entries.get(entryId);
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
    sleep_minutes: sleepFieldFromPull(data, 'sleep_minutes', existing?.sleep_minutes),
    sleep_quality: sleepFieldFromPull(data, 'sleep_quality', existing?.sleep_quality),
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

export interface HealthConnectSleepFillItem {
  entry_date: string;
  sleep_minutes: number;
}

/**
 * After Health Connect fills server ``sleep_minutes``, copy those values into
 * IndexedDB (and pending outbox payloads) fill-only.
 *
 * Sprint 4 emits sync revisions for imports, but Sync now never pulled them
 * into Dexie. A later offline/API-down mood edit then pushed explicit
 * ``sleep_minutes: null`` and wiped the wearable fill (#634 follow-up).
 *
 * Only dates whose server value matches the just-imported minutes are touched,
 * so a concurrent manual value (HC skipped) cannot be overwritten locally.
 *
 * A pending upsert whose ``client_ts`` is newer than the server row and still
 * has null sleep is treated as an intentional clear — do not resurrect sleep
 * into Dexie/outbox (that would undo the clear on the next push after a
 * ``skipped_existing_value`` Sync now).
 *
 * Outbox sleep is patched in place **without** bumping ``client_ts``. Inflating
 * the timestamp made a whole-row upsert win LWW over newer server writes
 * (cycle SHD erase, mood/energy from another device) while only sleep was
 * meant to be reconciled.
 */
export async function fillLocalSleepAfterHealthConnectImport(
  items: HealthConnectSleepFillItem[]
): Promise<number> {
  if (items.length === 0) return 0;

  const importedByDate = new Map(
    items.map((item) => [item.entry_date, item.sleep_minutes] as const)
  );
  const dates = [...importedByDate.keys()].sort();
  const startDate = dates[0];
  const endDate = dates[dates.length - 1];

  let serverEntries: EntryResponse[];
  try {
    serverEntries = await listEntries({
      start_date: startDate,
      end_date: endDate,
      limit: Math.min(500, Math.max(50, dates.length * 2)),
    });
  } catch {
    return 0;
  }

  const db = getOfflineDb();
  const pending = await listPendingChanges();
  let filled = 0;

  for (const serverEntry of serverEntries) {
    const importedMinutes = importedByDate.get(serverEntry.entry_date);
    if (importedMinutes == null) continue;
    if (serverEntry.slot !== 'day') continue;
    // Server must reflect our fill — skips manual-wins and unrelated rows.
    if (serverEntry.sleep_minutes !== importedMinutes) continue;

    let local = await db.entries.get(serverEntry.id);
    if (!local) {
      local = await findLocalEntryByDateSlot(serverEntry.entry_date, serverEntry.slot);
    }
    if (!local) continue;
    // Local manual (or prior fill) wins — never clobber a non-null local value.
    if (local.sleep_minutes != null) continue;

    const pendingForEntry = pending.filter(
      (change) => change.entity_id === local.id && change.operation === 'upsert'
    );
    // Newer pending null sleep = user cleared (or edited) after the server
    // value was written. Resurrecting sleep here undoes that intentional clear
    // once scheduleSync pushes the pending null.
    const newerNullSleepPending = pendingForEntry.some((change) => {
      const payload = change.payload;
      if (!payload || typeof payload !== 'object' || Array.isArray(payload)) return false;
      const current = payload as Record<string, unknown>;
      if (current.sleep_minutes != null) return false;
      return change.client_ts > serverEntry.updated_at;
    });
    if (newerNullSleepPending) continue;

    await db.entries.update(local.id, { sleep_minutes: importedMinutes });
    filled += 1;

    for (const change of pendingForEntry) {
      const payload = change.payload;
      if (!payload || typeof payload !== 'object' || Array.isArray(payload)) continue;
      const current = payload as Record<string, unknown>;
      // buildSyncEntryPayload always sends sleep_minutes (often null). Replace
      // null/missing only so a later push cannot wipe the HC fill when the
      // outbox already wins LWW. Do not bump client_ts — that inverted LWW
      // against newer server clears/edits. If client_ts is older than the
      // server row, push loses and server sleep (just filled) stays intact.
      if (current.sleep_minutes != null) continue;
      await db.change_log.update(change.seq!, {
        payload: {
          ...current,
          sleep_minutes: importedMinutes,
          // Defense in depth: never push stale cycle SHD over a server erase
          // if this outbox row still somehow wins LWW on its original ts.
          cycle_day: serverEntry.cycle_day ?? null,
          cycle_bleeding_level: serverEntry.cycle_bleeding_level ?? null,
        },
      });
    }
  }

  return filled;
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
        // Never clobber pending/conflict (or newer) local rows with a server snapshot —
        // that would wipe unsynced mood/note/energy edits from IndexedDB while the
        // outbox still holds them, and a later form hydrate/autosave can ack+rewrite
        // the outbox from the stale local row (data loss).
        if (shouldPreferLocalEntry(local, serverEntry.updated_at)) {
          if (entryHasCycleData(local)) {
            await db.entries.update(local.id, {
              cycle_day: null,
              cycle_bleeding_level: null,
            });
          }
          continue;
        }
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
            // Preserve non-cycle fields from the server snapshot — omitting
            // sleep here used to null IDB sleep via applyPulledEntry and
            // later push nulls after an offline edit (#636 follow-up).
            sleep_minutes: serverEntry.sleep_minutes ?? null,
            sleep_quality: serverEntry.sleep_quality ?? null,
            work_context: serverEntry.work_context,
            note: serverEntry.note,
            tag_ids: local.tag_ids,
            symptoms: local.symptoms,
          },
          serverEntry.updated_at,
          'synced'
        );
      }
    } catch {
      // Offline pull is best-effort; local scrub above still prevents stale SHD display.
    }
  }

  return cleared;
}
