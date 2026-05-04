/**
 * Symptoms API client — Issue #57 (Custom-Symptome, ADR-0008).
 *
 * Mirrors backend/app/schemas/symptom.py. All calls go through `apiFetch`,
 * which adds `credentials: 'include'` and handles single-flight refresh
 * on 401 (see ./client.ts).
 *
 * The symptom system has two surfaces (analog zum Tag-System):
 *   1. Symptom CRUD — defaults (read-only) plus the user's custom symptoms.
 *   2. Entry-symptom assignment — replace-set semantics on
 *      PUT /entries/{id}/symptoms.
 *
 * Privacy
 * -------
 * Symptom payloads are health data under DSGVO Art. 9 — keep them out
 * of console logs. The shared `apiFetch` helper already enforces this
 * for request bodies; consumers must do the same in component code.
 * Custom symptom names are sensitive too (see ADR-0008 § Privacy),
 * so the encryption-at-rest work in Issue #26 must include them.
 */

import { api } from './client';

// ---------------------------------------------------------------------------
// Constants — keep in sync with app/models/symptom.py
// ---------------------------------------------------------------------------

/** Hard upper bound — kept in sync with MAX_SYMPTOMS_PER_ENTRY in symptom.py. */
export const MAX_SYMPTOMS_PER_ENTRY = 32;

/** Visual scale bounds. The UI renders 4 dots (0..3); the backend
 * also enforces this range via Pydantic + a DB CHECK constraint. */
export const INTENSITY_MIN = 0;
export const INTENSITY_MAX = 3;

// ---------------------------------------------------------------------------
// DTOs
// ---------------------------------------------------------------------------

export interface SymptomResponse {
  id: string;
  user_id: string | null;
  slug: string;
  name: string;
  icon: string | null;
  is_default: boolean;
  created_at: string;
  updated_at: string;
}

export interface SymptomCreatePayload {
  slug: string;
  name: string;
  icon?: string | null;
}

export interface SymptomUpdatePayload {
  name?: string;
  icon?: string | null;
}

/** A single (symptom_id, intensity) selection on an entry. */
export interface SymptomEntry {
  symptom_id: string;
  intensity: number;
}

export interface EntrySymptomResponse {
  id: string;
  entry_id: string;
  user_id: string;
  symptom_id: string;
  intensity: number;
  created_at: string;
  updated_at: string;
}

// ---------------------------------------------------------------------------
// Calls — Symptom CRUD
// ---------------------------------------------------------------------------

/** GET /symptoms/default — public list of curated default symptoms (no auth). */
export async function listDefaultSymptoms(): Promise<SymptomResponse[]> {
  return api.get<SymptomResponse[]>('/symptoms/default');
}

/** GET /symptoms — defaults + the current user's custom symptoms. */
export async function listVisibleSymptoms(): Promise<SymptomResponse[]> {
  return api.get<SymptomResponse[]>('/symptoms');
}

/** POST /symptoms — create a custom symptom for the current user. */
export async function createSymptom(payload: SymptomCreatePayload): Promise<SymptomResponse> {
  return api.post<SymptomResponse>('/symptoms', payload);
}

/** PATCH /symptoms/{id} — update a custom symptom (defaults are read-only). */
export async function updateSymptom(
  id: string,
  payload: SymptomUpdatePayload
): Promise<SymptomResponse> {
  return api.patch<SymptomResponse>(`/symptoms/${id}`, payload);
}

/** DELETE /symptoms/{id} — delete a custom symptom (cascades to entry_symptoms). */
export async function deleteSymptom(id: string): Promise<void> {
  await api.delete(`/symptoms/${id}`);
}

// ---------------------------------------------------------------------------
// Calls — Entry-symptom assignment
// ---------------------------------------------------------------------------

/** GET /entries/{id}/symptoms — current symptom set on an entry. */
export async function listSymptomsForEntry(entryId: string): Promise<EntrySymptomResponse[]> {
  return api.get<EntrySymptomResponse[]>(`/entries/${entryId}/symptoms`);
}

/**
 * PUT /entries/{id}/symptoms — replace the entry's full symptom set.
 *
 * Replace-set semantics: pass the complete desired list. Sending an
 * empty array clears all symptoms on the entry. Each symptom_id must
 * be visible to the user (default or owned).
 */
export async function assignSymptomsToEntry(
  entryId: string,
  symptoms: SymptomEntry[]
): Promise<EntrySymptomResponse[]> {
  return api.put<EntrySymptomResponse[]>(`/entries/${entryId}/symptoms`, { symptoms });
}
