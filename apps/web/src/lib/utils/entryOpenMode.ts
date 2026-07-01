export type EntryOpenMode = 'quick' | 'full';

const STORAGE_KEY = 'cc_entry_open_mode';

export function getEntryOpenMode(): EntryOpenMode {
  if (typeof localStorage === 'undefined') return 'full';
  return localStorage.getItem(STORAGE_KEY) === 'quick' ? 'quick' : 'full';
}

export function setEntryOpenMode(mode: EntryOpenMode): void {
  if (typeof localStorage === 'undefined') return;
  localStorage.setItem(STORAGE_KEY, mode);
}
