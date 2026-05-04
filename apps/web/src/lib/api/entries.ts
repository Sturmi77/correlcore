/**
 * Entries API client — Issue #7.
 *
 * Mirrors backend/app/schemas/entry.py. All calls go through `apiFetch`,
 * which adds `credentials: 'include'` and handles single-flight refresh
 * on 401 (see ./client.ts).
 */

import { api } from './client';

// ---------------------------------------------------------------------------
// Enums — keep in sync with app/models/entry.py
// ---------------------------------------------------------------------------

export type EntrySlot = 'day' | 'morning' | 'noon' | 'evening';

export type WorkContext = 'homeoffice' | 'office' | 'vacation' | 'sick' | 'weekend' | 'travel';

// ---------------------------------------------------------------------------
// DTOs
// ---------------------------------------------------------------------------

export interface EntryResponse {
  id: string;
  user_id: string;
  entry_date: string; // ISO date YYYY-MM-DD
  slot: EntrySlot;
  mood_score: number;
  energy: number;
  stress: number;
  work_context: WorkContext;
  note: string | null;
  created_at: string;
  updated_at: string;
}

export interface EntryCreatePayload {
  entry_date: string; // ISO date YYYY-MM-DD
  slot?: EntrySlot;
  mood_score: number;
  energy: number;
  stress: number;
  work_context: WorkContext;
  note?: string;
}

export interface EntryUpdatePayload {
  mood_score?: number;
  energy?: number;
  stress?: number;
  work_context?: WorkContext;
  note?: string;
}

export interface EntryListQuery {
  start_date?: string;
  end_date?: string;
  limit?: number;
}

// ---------------------------------------------------------------------------
// Calls
// ---------------------------------------------------------------------------

/** POST /entries — create today's (or backdated up to 7 days) entry. */
export async function createEntry(payload: EntryCreatePayload): Promise<EntryResponse> {
  return api.post<EntryResponse>('/entries', payload);
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
  const qs = params.toString();
  const path = qs ? `/entries?${qs}` : '/entries';
  return api.get<EntryResponse[]>(path);
}

/** PATCH /entries/{id} — update within the 7-day window. */
export async function updateEntry(id: string, payload: EntryUpdatePayload): Promise<EntryResponse> {
  return api.patch<EntryResponse>(`/entries/${id}`, payload);
}
