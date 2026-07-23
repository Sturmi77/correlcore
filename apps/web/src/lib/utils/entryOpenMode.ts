export type EntryOpenMode = 'quick' | 'full';

const ENTRY_OPEN_MODE_STORAGE_KEY = 'cc_entry_open_mode';

export function getEntryOpenMode(): EntryOpenMode {
  if (typeof localStorage === 'undefined') return 'full';
  return localStorage.getItem(ENTRY_OPEN_MODE_STORAGE_KEY) === 'quick' ? 'quick' : 'full';
}

export function setEntryOpenMode(mode: EntryOpenMode): void {
  if (typeof localStorage === 'undefined') return;
  localStorage.setItem(ENTRY_OPEN_MODE_STORAGE_KEY, mode);
}
