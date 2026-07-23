/**
 * Persist the last authenticated user for offline cold starts.
 *
 * When `/auth/me` fails with a transport error, hydrate can restore this
 * snapshot so the shell stays authenticated and deferred sync remains usable.
 * Cleared on logout and definitive session expiry — never used as a security
 * boundary (API still enforces auth once reachable).
 */

import type { UserResponse } from '$lib/api/auth';

export const LAST_USER_STORAGE_KEY = 'cc_last_user';

export function cacheLastUser(user: UserResponse): void {
  if (typeof localStorage === 'undefined') return;
  try {
    localStorage.setItem(LAST_USER_STORAGE_KEY, JSON.stringify(user));
  } catch {
    // Quota / private mode — offline boot simply won't restore.
  }
}

export function readLastUser(): UserResponse | null {
  if (typeof localStorage === 'undefined') return null;
  try {
    const raw = localStorage.getItem(LAST_USER_STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<UserResponse>;
    if (typeof parsed.id !== 'string' || typeof parsed.email !== 'string') return null;
    return {
      id: parsed.id,
      email: parsed.email,
      display_name: parsed.display_name ?? null,
      is_verified: Boolean(parsed.is_verified),
    };
  } catch {
    return null;
  }
}

export function clearLastUser(): void {
  if (typeof localStorage === 'undefined') return;
  try {
    localStorage.removeItem(LAST_USER_STORAGE_KEY);
  } catch {
    // ignore
  }
}
