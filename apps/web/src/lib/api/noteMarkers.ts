export type NoteVisibility = 'full' | 'analysis_only' | 'hidden';

/**
 * Shape of a note marker as returned by the entry read API.
 *
 * Note markers are no longer captured or displayed in the UI (#890 / #893
 * removed the composer chips, #897 the read-only history rendering). The type
 * is retained because the backend still includes `note_markers[]` on entry
 * responses for historical/API-created rows until the table is retired.
 */
export interface EntryNoteMarkerResponse {
  id: string;
  entry_id: string;
  marker: string;
  source: 'user' | 'suggestion';
  created_at: string;
}
