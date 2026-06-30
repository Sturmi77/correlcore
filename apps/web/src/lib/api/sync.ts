/**
 * Offline sync API client — M4.1 (ADR-0036, docs/API.md §10).
 */

import { api } from './client';
import type { EntrySlot, WorkContext } from '$lib/contracts/apiContract';

export type SyncTableName = 'entries' | 'tags' | 'symptoms';
export type SyncChangeOperation = 'upsert' | 'delete';
export type SyncEntityType = 'entry' | 'tag' | 'symptom';

export interface SyncEntryPayload {
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
}

export interface SyncChange {
  seq: number;
  id: string;
  table: SyncTableName;
  operation: SyncChangeOperation;
  data: Record<string, unknown>;
  updated_at: string;
}

export interface SyncPushRequest {
  client_id: string;
  batch_id: string;
  changes: SyncChange[];
}

export interface SyncConflictReport {
  entity_id: string;
  entity_type: SyncEntityType;
  field_name: string;
  client_ts: string;
  server_ts: string;
  winner: 'server';
  client_value?: Record<string, unknown> | null;
  server_value?: Record<string, unknown> | null;
}

export interface SyncPushResponse {
  cursor: string;
  applied: number;
  skipped: number;
  conflicts: SyncConflictReport[];
  idempotent_replay: boolean;
}

export interface SyncPullResponse {
  cursor: string;
  changes: SyncChange[];
  has_more: boolean;
  server_time: string;
}

export interface SyncPullQuery {
  since?: string;
  limit?: number;
}

export async function pushSyncChanges(body: SyncPushRequest): Promise<SyncPushResponse> {
  return api.post<SyncPushResponse>('/sync/push', body);
}

export async function pullSyncChanges(query: SyncPullQuery = {}): Promise<SyncPullResponse> {
  const params = new URLSearchParams();
  if (query.since) params.set('since', query.since);
  if (query.limit !== undefined) params.set('limit', String(query.limit));
  const qs = params.toString();
  return api.get<SyncPullResponse>(`/sync/pull${qs ? `?${qs}` : ''}`);
}
