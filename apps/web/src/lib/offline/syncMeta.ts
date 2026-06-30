import { getOfflineDb } from './db';
import type { SyncMetaKey } from './types';

export async function getSyncMeta(key: SyncMetaKey | string): Promise<string | null> {
  const row = await getOfflineDb().sync_meta.get(key);
  return row?.value ?? null;
}

export async function setSyncMeta(key: SyncMetaKey | string, value: string): Promise<void> {
  await getOfflineDb().sync_meta.put({ key, value });
}

export async function deleteSyncMeta(key: SyncMetaKey | string): Promise<void> {
  await getOfflineDb().sync_meta.delete(key);
}
