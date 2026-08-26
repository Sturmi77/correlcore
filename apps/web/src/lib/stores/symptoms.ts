/**
 * Symptoms store — Issue #57 (Custom-Symptome, ADR-0008).
 *
 * In-memory cache of the symptom catalogue (defaults + custom symptoms).
 * The catalogue is small (≤ 50 custom + curated defaults), so we keep one flat
 * array in memory and refresh on demand. Symptoms have no category, so the
 * picker renders a single flat alphabetised list (defaults first, then
 * custom — see `symptomsList`).
 *
 * State shape mirrors the tags store: `idle | loading | ready | error`.
 */

import { writable, derived, get } from 'svelte/store';
import {
  createSymptom as apiCreateSymptom,
  deleteSymptom as apiDeleteSymptom,
  listVisibleSymptoms as apiListVisibleSymptoms,
  updateSymptom as apiUpdateSymptom,
  type SymptomCreatePayload,
  type SymptomResponse,
  type SymptomUpdatePayload,
} from '$lib/api/symptoms';

export type SymptomsState =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'ready'; symptoms: SymptomResponse[] }
  | { status: 'error'; message: string };

const _symptoms = writable<SymptomsState>({ status: 'idle' });

// Incremented on every reset (session boundary). An in-flight refresh compares
// the generation it captured at start against this; a mismatch means a reset
// happened mid-flight, so the resolved response belongs to a prior account and
// must not repopulate the store (#669).
let storeGeneration = 0;

export const symptoms = { subscribe: _symptoms.subscribe };

/**
 * Flat list of currently-known symptoms (defaults + custom), or [] when
 * not ready. Defaults come first, then custom; within each group sorted
 * alphabetically by display name (locale-aware) so the picker order is
 * stable across reloads.
 */
export const symptomsList = derived(_symptoms, ($s) => {
  if ($s.status !== 'ready') return [] as SymptomResponse[];
  const defaults = $s.symptoms.filter((s) => s.is_default);
  const custom = $s.symptoms.filter((s) => !s.is_default);
  defaults.sort((a, b) => a.name.localeCompare(b.name));
  custom.sort((a, b) => a.name.localeCompare(b.name));
  return [...defaults, ...custom];
});

/** Refresh the symptom catalogue from the server. */
export async function refreshSymptoms(): Promise<SymptomResponse[]> {
  const gen = storeGeneration;
  _symptoms.set({ status: 'loading' });
  try {
    const list = await apiListVisibleSymptoms();
    // A session boundary (resetSymptomsStore) bumped the generation while this
    // request for the previous account was in flight — drop the stale result
    // instead of restoring another user's symptoms over the new account's store.
    if (gen !== storeGeneration) return list;
    _symptoms.set({ status: 'ready', symptoms: list });
    return list;
  } catch (err) {
    if (gen !== storeGeneration) throw err;
    const message = err instanceof Error ? err.message : 'Failed to load symptoms';
    _symptoms.set({ status: 'error', message });
    throw err;
  }
}

/** Create a custom symptom and add it to the cache. */
export async function submitSymptom(payload: SymptomCreatePayload): Promise<SymptomResponse> {
  const created = await apiCreateSymptom(payload);
  const current = get(_symptoms);
  const existing = current.status === 'ready' ? current.symptoms : [];
  _symptoms.set({ status: 'ready', symptoms: [...existing, created] });
  return created;
}

/** Update a custom symptom in place in the cache. */
export async function patchSymptom(
  id: string,
  payload: SymptomUpdatePayload
): Promise<SymptomResponse> {
  const updated = await apiUpdateSymptom(id, payload);
  const current = get(_symptoms);
  if (current.status === 'ready') {
    _symptoms.set({
      status: 'ready',
      symptoms: current.symptoms.map((s) => (s.id === id ? updated : s)),
    });
  }
  return updated;
}

/** Delete a custom symptom and remove it from the cache. */
export async function removeSymptom(id: string): Promise<void> {
  await apiDeleteSymptom(id);
  const current = get(_symptoms);
  if (current.status === 'ready') {
    _symptoms.set({
      status: 'ready',
      symptoms: current.symptoms.filter((s) => s.id !== id),
    });
  }
}

/** Reset the cache — useful on logout. */
export function resetSymptomsStore(): void {
  // Bump the generation so any in-flight refreshSymptoms() for the previous
  // account drops its result instead of repopulating the store post-swap.
  storeGeneration += 1;
  _symptoms.set({ status: 'idle' });
}
