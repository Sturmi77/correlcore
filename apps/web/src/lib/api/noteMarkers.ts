import { api } from './client';

export type NoteVisibility = 'full' | 'analysis_only' | 'hidden';

export interface EntryNoteMarkerResponse {
  id: string;
  entry_id: string;
  marker: string;
  source: 'user' | 'suggestion';
  created_at: string;
}

export interface EntryNoteMarkerCreatePayload {
  marker: string;
  source?: 'user' | 'suggestion';
}

export const PREDEFINED_NOTE_MARKERS = [
  'work',
  'homeoffice',
  'social',
  'movement',
  'sleep_bad',
  'sleep_good',
  'stress',
  'conflict',
  'symptom',
  'travel',
  'achievement',
] as const;

export type PredefinedNoteMarker = (typeof PREDEFINED_NOTE_MARKERS)[number];

export async function addNoteMarker(
  entryId: string,
  payload: EntryNoteMarkerCreatePayload
): Promise<EntryNoteMarkerResponse> {
  return api.post<EntryNoteMarkerResponse>(`/entries/${entryId}/note-markers`, payload);
}

export async function deleteNoteMarker(entryId: string, markerId: string): Promise<void> {
  await api.delete(`/entries/${entryId}/note-markers/${markerId}`);
}

export async function listNoteMarkerSuggestions(): Promise<string[]> {
  return api.get<string[]>('/user/me/note-markers/suggestions');
}
