/**
 * Auth store — Issue #40 + M11 Sprint 3.
 *
 * Holds the current user (or null when unauthenticated).
 * Tokens are not stored here: browser → HttpOnly cookies; Capacitor →
 * in-memory sessionTokens (ADR-0006). This store is a UI mirror of
 * "is the user logged in?".
 *
 * Lifecycle:
 *   - On app boot: hydrate() probes /auth/me. 200 → user, 401 → null.
 *   - On login:    login() sets the user and returns it.
 *   - On logout:   logout() clears the user and session (cookies / memory).
 */

import { writable, derived, get } from 'svelte/store';
import {
  fetchCurrentUser,
  login as apiLogin,
  logout as apiLogout,
  type LoginPayload,
  type UserResponse,
} from '$lib/api/auth';
import { clearSessionTokens } from '$lib/api/sessionTokens';
import { disablePushNotifications, enablePushNotifications } from '$lib/native/pushNotifications';
import { resetInsightStore } from '$lib/stores/insights';
import { resetEntrySheetStore } from '$lib/stores/entrySheet';
import {
  clearOfflineDataForLogout,
  drainOfflineSyncForSessionChange,
  prepareOfflineDataForAuthenticatedUser,
} from '$lib/offline/session';

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

/** Probe /auth/me and set store. Idempotent — runs at most once per page load. */
export async function hydrate(): Promise<AuthState> {
  if (hydrated) return get(_auth);
  hydrated = true;
  try {
    const user = await fetchCurrentUser();
    if (user) {
      await prepareOfflineDataForAuthenticatedUser(user.id);
      _auth.set({ status: 'authenticated', user });
      void enablePushNotifications();
    } else {
      _auth.set({ status: 'anonymous' });
    }
  } catch {
    // Network failure — treat as anonymous so login UI shows.
    _auth.set({ status: 'anonymous' });
  }
  return get(_auth);
}

export async function login(payload: LoginPayload): Promise<UserResponse> {
  await drainOfflineSyncForSessionChange();
  const res = await apiLogin(payload);
  await prepareOfflineDataForAuthenticatedUser(res.user.id);
  resetInsightStore();
  resetEntrySheetStore();
  _auth.set({ status: 'authenticated', user: res.user });
  void enablePushNotifications();
  return res.user;
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
  resetInsightStore();
  resetEntrySheetStore();
  _auth.set({ status: 'anonymous' });
}

/**
 * Set the user manually after a flow that already established a session
 * (e.g. after verify-email + login in the same request chain).
 */
export async function setUser(user: UserResponse): Promise<void> {
  await prepareOfflineDataForAuthenticatedUser(user.id);
  resetInsightStore();
  resetEntrySheetStore();
  _auth.set({ status: 'authenticated', user });
  void enablePushNotifications();
}

/** Test-only: reset hydration state. */
export function _resetForTests(): void {
  hydrated = false;
  _auth.set({ status: 'loading' });
}
