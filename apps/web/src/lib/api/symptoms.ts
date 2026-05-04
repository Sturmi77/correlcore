/**
 * Symptoms API client — Issue #9.
 *
 * Mirrors backend/app/schemas/symptom.py. All calls go through `apiFetch`
 * which adds `credentials: 'include'` and handles single-flight refresh
 * on 401 (see ./client.ts).
 *
 * The symptom system has two surfaces:
 *   1. Standard catalogue — the closed set of canonical symptom keys
 *      (no auth required, the picker can render before login finishes).
 *   2. Entry-symptom assignment — replace-set semantics on
 *      PUT /entries/{id}/symptoms.
 *
 * Privacy
 * -------
 * Symptom payloads are health data under DSGVO Art. 9 — keep them out
 * of console logs. The shared `apiFetch` helper already enforces this
 * for request bodies; consumers must do the same in component code.
 */

import { api } from './client';

// ---------------------------------------------------------------------------
// Constants — keep in sync with app/models/symptom.py
// ---------------------------------------------------------------------------

/** The five standard symptom keys (M1). Order is alphabetical. */
export const STANDARD_SYMPTOM_KEYS = [
  'back_pain',
  'cold',
  'digestion',
  'fatigue',
  'headache',
] as const;

export type StandardSymptomKey = (typeof STANDARD_SYMPTOM_KEYS)[number];

/** Hard upper bound — kept in sync with MAX_SYMPTOMS_PER_ENTRY in symptom.py. */
export const MAX_SYMPTOMS_PER_ENTRY = 32;

/** Visual scale bounds. The UI renders 4 dots (0..3); the backend
 * also enforces this range via Pydantic + a DB CHECK constraint. */
export const INTENSITY_MIN = 0;
export const INTENSITY_MAX = 3;

// ---------------------------------------------------------------------------
// DTOs
// ---------------------------------------------------------------------------

export interface SymptomEntry {
  symptom_key: string;
  intensity: number;
}

export interface SymptomResponse {
  id: string;
  entry_id: string;
  user_id: string;
  symptom_key: string;
  intensity: number;
  created_at: string;
  updated_at: string;
}

export interface StandardSymptomKeyEntry {
  symptom_key: string;
}

export interface StandardSymptomKeyList {
  keys: StandardSymptomKeyEntry[];
}

// ---------------------------------------------------------------------------
// Calls — Standard catalogue
// ---------------------------------------------------------------------------

/** GET /symptoms/standard — public list of standard symptom keys (no auth). */
export async function listStandardSymptomKeys(): Promise<StandardSymptomKeyList> {
  return api.get<StandardSymptomKeyList>('/symptoms/standard');
}

// ---------------------------------------------------------------------------
// Calls — Entry-symptom assignment
// ---------------------------------------------------------------------------

/** GET /entries/{id}/symptoms — current symptom set on an entry. */
export async function listSymptomsForEntry(entryId: string): Promise<SymptomResponse[]> {
  return api.get<SymptomResponse[]>(`/entries/${entryId}/symptoms`);
}

/**
 * PUT /entries/{id}/symptoms — replace the entry's full symptom set.
 *
 * Replace-set semantics: pass the complete desired list. Sending an
 * empty array clears all symptoms on the entry. Symptom keys must be
 * unique within the request and present in `STANDARD_SYMPTOM_KEYS`.
 */
export async function assignSymptomsToEntry(
  entryId: string,
  symptoms: SymptomEntry[]
): Promise<SymptomResponse[]> {
  return api.put<SymptomResponse[]>(`/entries/${entryId}/symptoms`, { symptoms });
}
