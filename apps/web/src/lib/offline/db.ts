/**
 * Dexie offline database (M4.1 Sprint 3, ADR-0036 §5; M4.1.1 #258).
 *
 * Default name: `correlcore-offline`. Authenticated sessions use
 * `correlcore-offline-<userId>` for per-user partition.
 */

import Dexie, { type Table } from 'dexie';

import type { ChangeLogRow, LocalEntry, LocalSymptom, LocalTag, SyncMetaRow } from './types';

export const OFFLINE_DB_NAME = 'correlcore-offline';
export const OFFLINE_DB_VERSION = 2;

export function offlineDbNameForUser(userId: string): string {
  return `${OFFLINE_DB_NAME}-${userId}`;
}

export class CorrelCoreOfflineDB extends Dexie {
  entries!: Table<LocalEntry, string>;
  tags!: Table<LocalTag, string>;
  symptoms!: Table<LocalSymptom, string>;
  change_log!: Table<ChangeLogRow, number>;
  sync_meta!: Table<SyncMetaRow, string>;

  constructor(name = OFFLINE_DB_NAME) {
    super(name);
    this.version(1).stores({
      entries: 'id, entry_date, sync_state, updated_at',
      change_log: '++seq, status, entity_id, batch_id',
      sync_meta: 'key',
    });
    this.version(OFFLINE_DB_VERSION).stores({
      entries: 'id, entry_date, sync_state, updated_at',
      tags: 'id, slug, updated_at',
      symptoms: 'id, slug, updated_at',
      change_log: '++seq, status, entity_id, batch_id',
      sync_meta: 'key',
    });
  }
}

let dbInstance: CorrelCoreOfflineDB | null = null;
let dbInstanceName = OFFLINE_DB_NAME;

export function getOfflineDb(userId?: string | null): CorrelCoreOfflineDB {
  if (typeof indexedDB === 'undefined') {
    throw new Error('Offline database is only available in the browser');
  }
  const name = userId ? offlineDbNameForUser(userId) : dbInstanceName;
  if (!dbInstance || dbInstanceName !== name) {
    if (dbInstance?.isOpen()) {
      dbInstance.close();
    }
    dbInstanceName = name;
    dbInstance = new CorrelCoreOfflineDB(name);
  }
  return dbInstance;
}

/** Bind the singleton to a per-user partitioned database. */
export function bindOfflineDbToUser(userId: string): CorrelCoreOfflineDB {
  return getOfflineDb(userId);
}

/** Test helper — replace the singleton with a fresh database. */
export async function resetOfflineDbForTests(name = OFFLINE_DB_NAME): Promise<CorrelCoreOfflineDB> {
  if (dbInstance?.isOpen()) {
    dbInstance.close();
  }
  await Dexie.delete(name);
  dbInstanceName = name;
  dbInstance = new CorrelCoreOfflineDB(name);
  await dbInstance.open();
  return dbInstance;
}

/** Logout helper — delete the active (and optional legacy) database. */
export async function destroyOfflineDatabase(name?: string): Promise<void> {
  const target = name ?? dbInstanceName;
  if (dbInstance?.isOpen()) {
    dbInstance.close();
  }
  await Dexie.delete(target);
  if (target !== OFFLINE_DB_NAME) {
    try {
      await Dexie.delete(OFFLINE_DB_NAME);
    } catch {
      // Legacy DB may not exist.
    }
  }
  dbInstance = null;
  dbInstanceName = OFFLINE_DB_NAME;
}
