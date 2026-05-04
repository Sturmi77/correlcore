/**
 * Symptoms store — Issue #9.
 *
 * In-memory cache of the standard symptom-key catalogue. The catalogue
 * is a build-time constant on the backend (closed set of 5 keys), so
 * after the first fetch it never changes within a session.
 *
 * State shape mirrors the tags store: `idle | loading | ready | error`.
 *
 * The actual per-entry symptom selections live in the SymptomChecker
 * component's bound state — they're submitted via
 * `assignSymptomsToEntry` and not cached here, since they're tied to a
 * specific entry's lifecycle.
 */

import { writable, derived } from 'svelte/store';
import {
  STANDARD_SYMPTOM_KEYS,
  listStandardSymptomKeys as apiListStandardSymptomKeys,
} from '$lib/api/symptoms';

export type SymptomCatalogueState =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'ready'; keys: string[] }
  | { status: 'error'; message: string };

const _catalogue = writable<SymptomCatalogueState>({ status: 'idle' });

export const symptomCatalogue = { subscribe: _catalogue.subscribe };

/** Flat list of currently-known symptom keys, or [] when not ready. */
export const symptomKeysList = derived(_catalogue, ($s) => ($s.status === 'ready' ? $s.keys : []));

/**
 * Refresh the standard symptom catalogue from the server.
 *
 * On failure we fall back to the build-time constant `STANDARD_SYMPTOM_KEYS`
 * so the picker stays usable offline / when the backend is briefly
 * unavailable. The error is still recorded in the store so the caller
 * can show a non-blocking warning if it wants to.
 */
export async function refreshSymptomCatalogue(): Promise<string[]> {
  _catalogue.set({ status: 'loading' });
  try {
    const list = await apiListStandardSymptomKeys();
    const keys = list.keys.map((k) => k.symptom_key);
    _catalogue.set({ status: 'ready', keys });
    return keys;
  } catch (err) {
    const message = err instanceof Error ? err.message : 'Failed to load symptoms';
    // Best-effort fallback — populate from the local constant so the
    // checker still renders. The error is reported on the side-channel
    // for callers that care.
    _catalogue.set({ status: 'ready', keys: [...STANDARD_SYMPTOM_KEYS] });
    // Re-throw so the caller can decide whether to surface the message.
    throw new Error(message);
  }
}

/** Reset the cache — useful on logout. */
export function resetSymptomsStore(): void {
  _catalogue.set({ status: 'idle' });
}
