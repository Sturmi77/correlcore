/**
 * Auth store — Issue #40 + M11 Sprint 3 + #453 persistent session.
 *
 * Holds the current user (or null when unauthenticated).
 * Tokens are not stored here: browser → HttpOnly cookies; Capacitor →
 * in-memory sessionTokens (ADR-0006), optionally restored from
 * EncryptedSharedPreferences when „Angemeldet bleiben“ is on.
 *
 * Lifecycle:
 *   - On app boot: restore Capacitor secure session (if any), then
 *     hydrate() probes /auth/me. 200 → user, 401 → null, network error →
 *     restore last cached user in offline mode when available.
 *   - On login:    login() sets the user and returns it.
 *   - On logout:   logout() clears the user and session (cookies / memory / secure store).
 *   - On definitive credential failure after refresh: forceSessionExpired()
 *     flips the store to anonymous so the layout guard routes to login.
 */

import { writable, derived, get } from 'svelte/store';
import {
  fetchCurrentUser,
  login as apiLogin,
  logout as apiLogout,
  type LoginPayload,
  type UserResponse,
} from '$lib/api/auth';
import { NetworkError, SessionPersistenceError } from '$lib/api/client';
import { setRuntimeApiBase } from '$lib/api/apiBase';
import { usesBearerAuth } from '$lib/api/platform';
import { restoreSecureSession } from '$lib/api/secureSession';
import { onSessionExpired } from '$lib/api/sessionExpired';
import { clearSessionTokens, setSessionTokens } from '$lib/api/sessionTokens';
import { disablePushNotifications, enablePushNotifications } from '$lib/native/pushNotifications';
import { resetInsightStore } from '$lib/stores/insights';
import { resetEntrySheetStore } from '$lib/stores/entrySheet';
import { connectivity } from '$lib/stores/connectivity';
import { cacheLastUser, clearLastUser, readLastUser } from '$lib/stores/lastUserCache';
import {
  clearOfflineDataForLogout,
  drainOfflineSyncForSessionChange,
  prepareOfflineDataForAuthenticatedUser,
} from '$lib/offline/session';
import { clearAllOnboardingSuggestionStashes } from '$lib/utils/onboardingSuggestionStash';

export type AuthState =
  { status: 'loading' } | { status: 'authenticated'; user: UserResponse } | { status: 'anonymous' };

const _auth = writable<AuthState>({ status: 'loading' });

/** Reactive store — read-only from outside. */
export const auth = { subscribe: _auth.subscribe };

/** Convenience derived stores. */
export const currentUser = derived(_auth, ($a) => ($a.status === 'authenticated' ? $a.user : null));
export const isAuthenticated = derived(_auth, ($a) => $a.status === 'authenticated');
export const isAuthLoading = derived(_auth, ($a) => $a.status === 'loading');

let hydrated = false;

/**
 * Capacitor cold start: load refresh/access from EncryptedSharedPreferences
 * into memory before /auth/me (Issue #453).
 */
async function restoreCapacitorSessionIfNeeded(): Promise<void> {
  if (!usesBearerAuth()) return;
  const saved = await restoreSecureSession();
  if (!saved?.refreshToken) return;
  if (saved.apiBase) {
    setRuntimeApiBase(saved.apiBase);
  }
  setSessionTokens({
    access_token: saved.accessToken,
    refresh_token: saved.refreshToken,
    remember_me: true,
  });
}

async function becomeAuthenticated(
  user: UserResponse,
  options: { enablePush: boolean }
): Promise<void> {
  // Drain in-flight offline work under the *outgoing* identity before rebinding
  // the DB. login()/logout() already drain up front, but reconnectSession(),
  // hydrate() and setUser() reach here without one: prepareOfflineDataFor…()
  // rebinds IndexedDB to `user` while `get(auth)` still returns the previous
  // user, so an autosave's assertPersistActor() check passes yet the write lands
  // in the new account's DB. Draining here closes that window for every caller.
  await drainOfflineSyncForSessionChange();
  cacheLastUser(user);
  await prepareOfflineDataForAuthenticatedUser(user.id);
  _auth.set({ status: 'authenticated', user });
  if (options.enablePush) {
    void enablePushNotifications();
  }
}

/**
 * Drop local session UI state after a definitive credential failure.
 * Keeps Dexie offline data so the same user can resume after re-login.
 */
export function forceSessionExpired(): void {
  clearSessionTokens();
  clearLastUser();
  connectivity.markServerReachable(true);
  resetInsightStore();
  resetEntrySheetStore();
  _auth.set({ status: 'anonymous' });
}

onSessionExpired(forceSessionExpired);

/** Probe /auth/me and set store. Idempotent — runs at most once per page load. */
export async function hydrate(): Promise<AuthState> {
  if (hydrated) return get(_auth);
  hydrated = true;
  try {
    await restoreCapacitorSessionIfNeeded();
    const user = await fetchCurrentUser();
    if (user) {
      connectivity.markServerReachable(true);
      await becomeAuthenticated(user, { enablePush: true });
    } else {
      connectivity.markServerReachable(true);
      clearLastUser();
      _auth.set({ status: 'anonymous' });
    }
  } catch (err) {
    if (
      err instanceof NetworkError ||
      (err instanceof TypeError && err.message.includes('fetch'))
    ) {
      const cached = readLastUser();
      if (cached) {
        connectivity.markServerReachable(false);
        // Offline boot: keep the shell authenticated against the last known user.
        await becomeAuthenticated(cached, { enablePush: false });
        return get(_auth);
      }
    }
    // Unknown failure or no cached user — show login.
    _auth.set({ status: 'anonymous' });
  }
  return get(_auth);
}

/**
 * Re-probe the API after the user retries from the offline banner.
 * Restores a live session or forces login when credentials died while offline.
 */
export async function reconnectSession(): Promise<'online' | 'offline' | 'anonymous'> {
  try {
    const user = await fetchCurrentUser();
    if (user) {
      connectivity.markServerReachable(true);
      await becomeAuthenticated(user, { enablePush: true });
      return 'online';
    }
    forceSessionExpired();
    return 'anonymous';
  } catch (err) {
    if (err instanceof NetworkError) {
      connectivity.markServerReachable(false);
      return 'offline';
    }
    connectivity.markServerReachable(false);
    return 'offline';
  }
}

/**
 * Confirm the browser actually holds a session after an auth response that
 * may have set HttpOnly cookies (or Capacitor Bearer tokens).
 *
 * Auth JSON can return 200 while Set-Cookie never sticks (ADR-0040 proxy /
 * Secure mismatch). A null /auth/me means persistence failed — not bad
 * credentials — so callers surface SessionPersistenceError instead of a
 * 401 "wrong password" / "invalid token" mapping.
 *
 * When `expectedUser` is provided, the probed identity must match. Otherwise
 * a stripped Set-Cookie can leave a prior account's cookies in place and
 * `/auth/me` would silently authenticate the wrong user (cross-account
 * writes after verify-email / reset-password / login).
 */
async function requirePersistedSession(expectedUser?: UserResponse): Promise<UserResponse> {
  const sessionUser = await fetchCurrentUser();
  if (!sessionUser || (expectedUser && sessionUser.id !== expectedUser.id)) {
    clearSessionTokens();
    throw new SessionPersistenceError('/auth/me');
  }
  return sessionUser;
}

export async function login(payload: LoginPayload): Promise<UserResponse> {
  await drainOfflineSyncForSessionChange();
  const loginResult = await apiLogin(payload);
  // Credentials were accepted (apiLogin returned 200); probe before UI auth.
  const sessionUser = await requirePersistedSession(loginResult.user);
  connectivity.markServerReachable(true);
  resetInsightStore();
  resetEntrySheetStore();
  await becomeAuthenticated(sessionUser, { enablePush: true });
  return sessionUser;
}

export async function logout(): Promise<void> {
  await drainOfflineSyncForSessionChange();
  // Unregister FCM while the session is still authenticated — apiLogout()
  // clears Bearer tokens in finally, which would 401 DELETE /devices/push-token.
  await disablePushNotifications();
  try {
    await apiLogout();
  } catch {
    // Best-effort — even if the call fails, clear local state.
    clearSessionTokens();
  }
  await clearOfflineDataForLogout();
  clearAllOnboardingSuggestionStashes();
  clearLastUser();
  resetInsightStore();
  resetEntrySheetStore();
  _auth.set({ status: 'anonymous' });
}

/**
 * Finish an auth flow that already returned a TokenResponse (verify-email,
 * reset-password). Probes /auth/me before marking the UI authenticated —
 * same cookie-persistence class as login (ADR-0040). The probe must match
 * the auth-response user so a stripped Set-Cookie cannot leave a prior
 * account's session in place.
 */
export async function setUser(userFromAuthResponse: UserResponse): Promise<void> {
  const sessionUser = await requirePersistedSession(userFromAuthResponse);
  connectivity.markServerReachable(true);
  resetInsightStore();
  resetEntrySheetStore();
  await becomeAuthenticated(sessionUser, { enablePush: true });
}

/** Test-only: reset hydration state. */
export function _resetForTests(): void {
  hydrated = false;
  _auth.set({ status: 'loading' });
  clearLastUser();
  connectivity._resetForTests();
}
