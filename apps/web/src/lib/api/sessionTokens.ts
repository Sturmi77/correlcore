/**
 * In-memory JWT pair for Capacitor (ADR-0006 Phase 2).
 *
 * Never persisted to localStorage / sessionStorage. Cleared on logout and
 * failed refresh. Browser cookie path does not use this module.
 *
 * Android Glance widget: access + refresh are mirrored to a native
 * SharedPreferences store via {@link mirrorWidgetCredentials} (M11 exception)
 * so WorkManager can rotate after the access JWT TTL.
 */

import { clearWidgetCredentials, mirrorWidgetCredentials } from './widgetCredentials';

let accessToken: string | null = null;
let refreshToken: string | null = null;

export function getAccessToken(): string | null {
  return accessToken;
}

export function getRefreshToken(): string | null {
  return refreshToken;
}

/** Store both tokens after login / refresh / verify / reset (opt-in body). */
export function setSessionTokens(tokens: {
  access_token?: string | null;
  refresh_token?: string | null;
}): void {
  if (tokens.access_token) accessToken = tokens.access_token;
  if (tokens.refresh_token) refreshToken = tokens.refresh_token;
  void mirrorWidgetCredentials(accessToken, refreshToken);
}

export function clearSessionTokens(): void {
  accessToken = null;
  refreshToken = null;
  void clearWidgetCredentials();
}

/** Test-only. */
export function _resetSessionTokensForTests(): void {
  accessToken = null;
  refreshToken = null;
}
