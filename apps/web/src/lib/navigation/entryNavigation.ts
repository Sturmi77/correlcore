import { buildOpenEntryPath, entryWorkspacePath, type EntryNavigationDate } from './openEntry';

/** All viewports use the Home entry sheet (O-08). */
export function prefersEntrySheet(_width?: number): boolean {
  return true;
}

export function resolveEntryPath(date?: EntryNavigationDate, _width?: number): string {
  return buildOpenEntryPath(date);
}

/** @deprecated Legacy desktop workspace path — redirects to the global entry sheet. */
export function legacyEntryWorkspacePath(date?: EntryNavigationDate): string {
  return entryWorkspacePath(date);
}
