import type { EntrySlot, WorkContext } from '$lib/contracts/apiContract';

export type SyncState = 'local' | 'pending' | 'synced' | 'conflict';

export type ChangeLogStatus = 'pending' | 'acked' | 'failed';

export type ChangeLogOperation = 'upsert' | 'delete';

export type OfflineEntityType = 'entry' | 'tag' | 'symptom';

export interface LocalEntry {
  id: string;
  entry_date: string;
  slot: EntrySlot;
  mood_score: number;
  energy: number;
  stress: number;
  cycle_day: number | null;
  work_context: WorkContext;
  note: string | null;
  tag_ids: string[];
  symptoms: Record<string, number>;
  updated_at: string;
  sync_state: SyncState;
}

export interface ChangeLogRow {
  seq?: number;
  batch_id: string;
  entity_type: OfflineEntityType;
  entity_id: string;
  operation: ChangeLogOperation;
  payload: Record<string, unknown>;
  client_ts: string;
  status: ChangeLogStatus;
}

export interface SyncMetaRow {
  key: string;
  value: string;
}

export const SYNC_META_KEYS = {
  clientId: 'client_id',
  lastPullCursor: 'last_pull_cursor',
  lastPushAt: 'last_push_at',
  lastPullAt: 'last_pull_at',
} as const;

export type SyncMetaKey = (typeof SYNC_META_KEYS)[keyof typeof SYNC_META_KEYS];
