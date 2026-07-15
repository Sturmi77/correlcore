import { api } from './client';

export interface EntryNoteSignalResponse {
  id: string;
  entry_id: string;
  signal: string;
  confidence: number;
  source_span: string | null;
  extractor_v: string;
  created_at: string;
}

export async function listNoteSignals(entryId: string): Promise<EntryNoteSignalResponse[]> {
  return api.get<EntryNoteSignalResponse[]>(`/entries/${entryId}/note-signals`);
}

export type SignalConfidenceBand = 'low' | 'medium' | 'high';

/** Map a 0–1 extraction confidence to a three-band label (ADR-N-02 display). */
export function signalConfidenceBand(score: number): SignalConfidenceBand {
  if (score >= 0.85) return 'high';
  if (score >= 0.7) return 'medium';
  return 'low';
}
