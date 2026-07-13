/**
 * Append-only offline change outbox (ADR-0036 §5).
 */

import { getOfflineDb } from './db';
import type { ChangeLogRow, ChangeLogStatus } from './types';

export type AppendChangeInput = Omit<ChangeLogRow, 'seq' | 'status'> & {
  status?: ChangeLogStatus;
};

export async function appendChange(input: AppendChangeInput): Promise<number> {
  const db = getOfflineDb();
  const seq = await db.change_log.add({
    ...input,
    status: input.status ?? 'pending',
  });
  return seq;
}

export async function getChange(seq: number): Promise<ChangeLogRow | undefined> {
  return getOfflineDb().change_log.get(seq);
}

export async function listChangesByStatus(status: ChangeLogStatus): Promise<ChangeLogRow[]> {
  return getOfflineDb().change_log.where('status').equals(status).sortBy('seq');
}

export async function listPendingChanges(): Promise<ChangeLogRow[]> {
  return listChangesByStatus('pending');
}

export async function getLastAppliedSeq(): Promise<number> {
  const last = await getOfflineDb().change_log.orderBy('seq').last();
  return last?.seq ?? 0;
}

export async function markChangeStatus(seq: number, status: ChangeLogStatus): Promise<void> {
  await getOfflineDb().change_log.update(seq, { status });
}

/** Drop stale outbox rows for an entity before appending a newer upsert. */
export async function ackPendingChangesForEntity(entityId: string): Promise<void> {
  const pending = await listPendingChanges();
  await Promise.all(
    pending
      .filter((row) => row.entity_id === entityId)
      .map((row) => markChangeStatus(row.seq!, 'acked'))
  );
}
