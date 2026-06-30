/** Query flag: Home opens the entry sheet once, then strips the param. */
export const OPEN_ENTRY_QUERY = 'openEntry';

export const OPEN_ENTRY_HOME_PATH = `/?${OPEN_ENTRY_QUERY}=1`;

export function isOpenEntryRequested(searchParams: URLSearchParams): boolean {
  return searchParams.get(OPEN_ENTRY_QUERY) === '1';
}
