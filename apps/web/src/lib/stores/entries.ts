/**
 * Entries store — Issue #7.
 *
 * Light client-side cache of the user's recent entries. The store is
 * deliberately small: the M4 offline-sync layer (ADR-0009 / Issue #10)
 * will own the long-term cache; this is just the in-memory mirror so the
 * timeline view doesn't need to refetch on every navigation.
 *
 * State shape mirrors the auth store: `loading | ready | error`.
 */

import { writable, derived, get } from 'svelte/store';
import {
  createEntry as apiCreateEntry,
  listEntries as apiListEntries,
  type EntryCreatePayload,
  type EntryResponse,
} from '$lib/api/entries';

export type EntriesState =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'ready'; entries: EntryResponse[] }
  | { status: 'error'; message: string };

const _entries = writable<EntriesState>({ status: 'idle' });

// Incremented on every reset (session boundary). An in-flight refresh compares
// the generation it captured at start against this; a mismatch means a reset
// happened mid-flight, so the resolved response belongs to a prior account and
// must not repopulate the store (#669).
let storeGeneration = 0;

export const entries = { subscribe: _entries.subscribe };

export const entriesList = derived(_entries, ($s) => ($s.status === 'ready' ? $s.entries : []));

/** Refresh the timeline from the server. */
export async function refreshEntries(limit = 30): Promise<EntryResponse[]> {
  const gen = storeGeneration;
  _entries.set({ status: 'loading' });
  try {
    const list = await apiListEntries({ limit });
    // A session boundary (resetEntriesStore) bumped the generation while this
    // request for the previous account was in flight — drop the stale result
    // instead of restoring another user's entries over the new account's store.
    if (gen !== storeGeneration) return list;
    _entries.set({ status: 'ready', entries: list });
    return list;
  } catch (err) {
    if (gen !== storeGeneration) throw err;
    const message = err instanceof Error ? err.message : 'Failed to load entries';
    _entries.set({ status: 'error', message });
    throw err;
  }
}

/** Create a new entry and prepend it to the cache. */
export async function submitEntry(payload: EntryCreatePayload): Promise<EntryResponse> {
  const created = await apiCreateEntry(payload);
  const current = get(_entries);
  const existing = current.status === 'ready' ? current.entries : [];
  _entries.set({ status: 'ready', entries: [created, ...existing] });
  return created;
}

/** Reset the cache — useful on logout. */
export function resetEntriesStore(): void {
  // Bump the generation so any in-flight refreshEntries() for the previous
  // account drops its result instead of repopulating the store post-swap.
  storeGeneration += 1;
  _entries.set({ status: 'idle' });
}
