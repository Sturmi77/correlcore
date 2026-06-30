/**
 * Clear offline user data on logout (M4.1 review fix — per-user isolation).
 */

import { CLIENT_ID_STORAGE_KEY } from './clientId';
import { destroyOfflineDatabase } from './db';
import { resetSyncOrchestratorForTests } from './syncOrchestrator';

/** Wipe Dexie data and client identity so the next account starts clean. */
export async function clearOfflineDataForLogout(): Promise<void> {
  if (typeof window === 'undefined') {
    return;
  }
  if (typeof localStorage !== 'undefined') {
    localStorage.removeItem(CLIENT_ID_STORAGE_KEY);
  }
  if (typeof indexedDB !== 'undefined') {
    await destroyOfflineDatabase();
  }
  resetSyncOrchestratorForTests();
}
