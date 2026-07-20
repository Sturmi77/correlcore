/**
 * Page-level refresh registry for pull-to-refresh.
 *
 * Authenticated screens register a handler while mounted. The shared
 * PullToRefresh chrome in the app layout invokes the active handler when
 * the user pulls down at the top of the scroll container.
 */

import { derived, get, writable } from 'svelte/store';

export type PageRefreshHandler = () => void | Promise<void>;

const handlerStore = writable<PageRefreshHandler | null>(null);
const refreshingStore = writable(false);

export function registerPageRefresh(handler: PageRefreshHandler): () => void {
  handlerStore.set(handler);
  return () => {
    handlerStore.update((current) => (current === handler ? null : current));
  };
}

export async function runRegisteredPageRefresh(): Promise<boolean> {
  const handler = get(handlerStore);
  if (!handler || get(refreshingStore)) return false;
  refreshingStore.set(true);
  try {
    await handler();
    return true;
  } finally {
    refreshingStore.set(false);
  }
}

export const pageRefresh = {
  subscribe: derived([handlerStore, refreshingStore], ([$handler, $refreshing]) => ({
    hasHandler: $handler !== null,
    refreshing: $refreshing,
  })).subscribe,
};
