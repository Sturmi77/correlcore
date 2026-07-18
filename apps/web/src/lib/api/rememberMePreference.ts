/**
 * UX-only preference for the login „Angemeldet bleiben“ checkbox.
 * Never stores tokens — only a boolean in localStorage (Issue #453).
 */

export const REMEMBER_ME_STORAGE_KEY = 'cc_remember_me';

export function readRememberMePreference(defaultValue = true): boolean {
  if (typeof localStorage === 'undefined') return defaultValue;
  try {
    const raw = localStorage.getItem(REMEMBER_ME_STORAGE_KEY);
    if (raw === null) return defaultValue;
    return raw === 'true' || raw === '1';
  } catch {
    return defaultValue;
  }
}

export function writeRememberMePreference(value: boolean): void {
  if (typeof localStorage === 'undefined') return;
  try {
    localStorage.setItem(REMEMBER_ME_STORAGE_KEY, value ? 'true' : 'false');
  } catch {
    /* ignore quota / private mode */
  }
}
