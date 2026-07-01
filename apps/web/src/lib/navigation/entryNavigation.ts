import { DESKTOP_SHELL_BREAKPOINT_PX } from '$lib/ui/surfaceContract';
import { buildOpenEntryPath, entryWorkspacePath, type EntryNavigationDate } from './openEntry';

/** Mobile and narrow viewports use the Home entry sheet; desktop uses `/entries/new`. */
export function prefersEntrySheet(width?: number): boolean {
  if (width !== undefined) return width < DESKTOP_SHELL_BREAKPOINT_PX;
  if (typeof window === 'undefined') return true;
  return window.matchMedia(`(max-width: ${DESKTOP_SHELL_BREAKPOINT_PX - 1}px)`).matches;
}

export function resolveEntryPath(date?: EntryNavigationDate, width?: number): string {
  return prefersEntrySheet(width) ? buildOpenEntryPath(date) : entryWorkspacePath(date);
}
