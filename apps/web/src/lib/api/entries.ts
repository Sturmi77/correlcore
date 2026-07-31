/**
 * Entries API client — Issue #7.
 *
 * Mirrors backend/app/schemas/entry.py. All calls go through `apiFetch`,
 * which adds `credentials: 'include'` and handles single-flight refresh
 * on 401 (see ./client.ts).
 */

import { api } from './client';
import type { EntryNoteMarkerResponse, NoteVisibility } from './noteMarkers';
import type { EntryNoteSignalResponse } from './noteSignals';
import type { EntrySlot, EntrySource, WorkContext } from '$lib/contracts/apiContract';
import type { TagResponse } from './tags';

export type { EntrySlot, EntrySource, WorkContext } from '$lib/contracts/apiContract';
export type { NoteVisibility } from './noteMarkers';

// ---------------------------------------------------------------------------
// DTOs
// ---------------------------------------------------------------------------

export type BleedingLevel = 'none' | 'spotting' | 'light' | 'medium' | 'heavy';

export interface EntryResponse {
  id: string;
  user_id: string;
  entry_date: string; // ISO date YYYY-MM-DD
  slot: EntrySlot;
  mood_score: number;
  energy: number;
  stress: number;
  cycle_day: number | null;
  cycle_bleeding_level?: BleedingLevel | null;
  source: EntrySource;
  work_context: WorkContext;
  note: string | null;
  note_raw?: string | null;
  note_summary_short?: string | null;
  note_visibility?: NoteVisibility;
  note_updated_at?: string | null;
  note_markers?: EntryNoteMarkerResponse[];
  note_signals?: EntryNoteSignalResponse[];
  created_at: string;
  updated_at: string;
}

export interface EntryCreatePayload {
  entry_date: string; // ISO date YYYY-MM-DD
  slot?: EntrySlot;
  mood_score: number;
  energy: number;
  stress: number;
  cycle_day?: number | null;
  cycle_bleeding_level?: BleedingLevel | null;
  source?: EntrySource;
  work_context: WorkContext;
  note?: string;
  note_raw?: string;
  note_summary_short?: string;
  note_visibility?: NoteVisibility;
}

export interface EntryBatchCreatePayload {
  entries: EntryCreatePayload[];
}

export interface EntryUpdatePayload {
  mood_score?: number;
  energy?: number;
  stress?: number;
  slot?: EntrySlot;
  cycle_day?: number | null;
  cycle_bleeding_level?: BleedingLevel | null;
  work_context?: WorkContext;
  note?: string;
  note_raw?: string;
  note_summary_short?: string;
  note_visibility?: NoteVisibility;
}

export interface EntryListQuery {
  start_date?: string;
  end_date?: string;
  limit?: number;
  has_note?: boolean;
}

export interface EntryDeltaQuery {
  entry_date: string;
  slot?: EntrySlot;
}

export interface EntryMetrics {
  entry_date: string;
  slot: EntrySlot;
  mood_score: number;
  energy: number;
  stress: number;
}

export interface EntryMetricDelta {
  mood: number | null;
  energy: number | null;
  stress: number | null;
}

export interface EntryDeltaResponse {
  today: EntryMetrics | null;
  previous: EntryMetrics | null;
  delta: EntryMetricDelta;
  shared_tags: TagResponse[];
}

// ---------------------------------------------------------------------------
// Calls
// ---------------------------------------------------------------------------

/** POST /entries — create today's (or backdated up to 7 local days) entry. */
export async function createEntry(payload: EntryCreatePayload): Promise<EntryResponse> {
  return api.post<EntryResponse>('/entries', payload);
}

/** POST /entries/batch — create up to seven retrospective onboarding entries. */
export async function createEntryBatch(payload: EntryBatchCreatePayload): Promise<EntryResponse[]> {
  return api.post<EntryResponse[]>('/entries/batch', payload);
}

/** GET /entries/{id} — fetch a single entry. */
export async function fetchEntry(id: string): Promise<EntryResponse> {
  return api.get<EntryResponse>(`/entries/${id}`);
}

/** GET /entries — list entries newest-first, optionally filtered by date range. */
export async function listEntries(query: EntryListQuery = {}): Promise<EntryResponse[]> {
  const params = new URLSearchParams();
  if (query.start_date) params.set('start_date', query.start_date);
  if (query.end_date) params.set('end_date', query.end_date);
  if (query.limit !== undefined) params.set('limit', String(query.limit));
  if (query.has_note !== undefined) params.set('has_note', String(query.has_note));
  const qs = params.toString();
  const path = qs ? `/entries?${qs}` : '/entries';
  return api.get<EntryResponse[]>(path);
}

/** PATCH /entries/{id} — update within the 7-day window. */
/** GET /entries/delta - day-over-day comparison for one entry date and slot. */
export async function fetchEntryDelta(query: EntryDeltaQuery): Promise<EntryDeltaResponse> {
  const params = new URLSearchParams();
  params.set('entry_date', query.entry_date);
  if (query.slot) params.set('slot', query.slot);
  return api.get<EntryDeltaResponse>(`/entries/delta?${params.toString()}`);
}

export async function updateEntry(id: string, payload: EntryUpdatePayload): Promise<EntryResponse> {
  return api.patch<EntryResponse>(`/entries/${id}`, payload);
}

/** DELETE /entries/cycle-data — clear cycle SHD fields for all entries (ADR-0033). */
export async function deleteCycleData(): Promise<{ cleared_entries: number }> {
  return api.delete<{ cleared_entries: number }>('/entries/cycle-data');
}
