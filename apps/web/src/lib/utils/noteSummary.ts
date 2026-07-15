/** Note preview helper — mirrors backend `note_summary.py` (ADR-N-01). */

export const NOTE_SUMMARY_MAX_LENGTH = 120;

const SENTENCE_END = /[.!?]\s/;

export function computeNoteSummaryShort(
  note: string | null | undefined,
  maxLength = NOTE_SUMMARY_MAX_LENGTH
): string | null {
  if (note == null) return null;
  const text = note.trim();
  if (!text) return null;

  const match = SENTENCE_END.exec(text);
  let candidate: string;
  if (match && match.index + 1 <= maxLength) {
    candidate = text.slice(0, match.index + 1).trim();
  } else {
    candidate = text;
  }

  if (candidate.length <= maxLength) return candidate;
  return `${candidate.slice(0, maxLength - 1).trimEnd()}…`;
}

export function hasNote(entry: {
  note?: string | null;
  note_raw?: string | null;
  note_summary_short?: string | null;
}): boolean {
  const body = entry.note ?? entry.note_raw;
  if (typeof body === 'string' && body.trim().length > 0) return true;
  return Boolean(entry.note_summary_short && entry.note_summary_short.trim().length > 0);
}
