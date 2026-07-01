/** Query flag: Home opens the entry sheet once, then strips the param. */
export const OPEN_ENTRY_QUERY = 'openEntry';

/** Optional ISO date passed with openEntry to pre-select the entry date. */
export const ENTRY_DATE_QUERY = 'date';

export const OPEN_ENTRY_HOME_PATH = `/?${OPEN_ENTRY_QUERY}=1`;

export type EntryNavigationDate = string;

export function isOpenEntryRequested(searchParams: URLSearchParams): boolean {
  return searchParams.get(OPEN_ENTRY_QUERY) === '1';
}

export function entryDateFromSearchParams(
  searchParams: URLSearchParams
): EntryNavigationDate | null {
  const raw = searchParams.get(ENTRY_DATE_QUERY);
  if (!raw || !/^\d{4}-\d{2}-\d{2}$/.test(raw)) return null;
  return raw;
}

export function buildOpenEntryPath(date?: EntryNavigationDate): string {
  const params = new URLSearchParams({ [OPEN_ENTRY_QUERY]: '1' });
  if (date) params.set(ENTRY_DATE_QUERY, date);
  return `/?${params}`;
}

export function entryWorkspacePath(date?: EntryNavigationDate): string {
  if (!date) return '/entries/new';
  return `/entries/new?${ENTRY_DATE_QUERY}=${encodeURIComponent(date)}`;
}
