/**
 * Dexie offline database (M4.1 Sprint 3, ADR-0036 §5).
 *
 * Database name: `correlcore-offline` (version 1).
 * Browser-only — call `getOfflineDb()` from client code or tests with IndexedDB.
 */

import Dexie, { type Table } from 'dexie';

import type { ChangeLogRow, LocalEntry, SyncMetaRow } from './types';

export const OFFLINE_DB_NAME = 'correlcore-offline';
export const OFFLINE_DB_VERSION = 1;

export class CorrelCoreOfflineDB extends Dexie {
  entries!: Table<LocalEntry, string>;
  change_log!: Table<ChangeLogRow, number>;
  sync_meta!: Table<SyncMetaRow, string>;

  constructor(name = OFFLINE_DB_NAME) {
    super(name);
    this.version(OFFLINE_DB_VERSION).stores({
      entries: 'id, entry_date, sync_state, updated_at',
      change_log: '++seq, status, entity_id, batch_id',
      sync_meta: 'key',
    });
  }
}

let dbInstance: CorrelCoreOfflineDB | null = null;

export function getOfflineDb(): CorrelCoreOfflineDB {
  if (typeof indexedDB === 'undefined') {
    throw new Error('Offline database is only available in the browser');
  }
  if (!dbInstance) {
    dbInstance = new CorrelCoreOfflineDB();
  }
  return dbInstance;
}

/** Test helper — replace the singleton with a fresh in-memory database. */
export async function resetOfflineDbForTests(name = OFFLINE_DB_NAME): Promise<CorrelCoreOfflineDB> {
  if (dbInstance?.isOpen()) {
    dbInstance.close();
  }
  await Dexie.delete(name);
  dbInstance = new CorrelCoreOfflineDB(name);
  await dbInstance.open();
  return dbInstance;
}
