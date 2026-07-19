/**
 * In-memory JWT pair for Capacitor (ADR-0006 Phase 2).
 *
 * Never persisted to localStorage / sessionStorage. Cleared on logout and
 * failed refresh. Browser cookie path does not use this module.
 *
 * When „Angemeldet bleiben“ is on, refresh (+ access) are also written to
 * Android EncryptedSharedPreferences via {@link persistSecureSession}
 * (Issue #453) so cold starts can restore the WebView session.
 *
 * Android Glance widget: access + refresh are mirrored to a native
 * SharedPreferences store via {@link mirrorWidgetCredentials} (M11 exception)
 * so WorkManager can rotate after the access JWT TTL — only when remember is on.
 */

import { clearSecureSession, persistSecureSession } from './secureSession';
import { clearWidgetCredentials, mirrorWidgetCredentials } from './widgetCredentials';

let accessToken: string | null = null;
let refreshToken: string | null = null;
/** Whether the current Capacitor session should survive process death. */
let rememberMe = true;

export function getAccessToken(): string | null {
  return accessToken;
}

export function getRefreshToken(): string | null {
  return refreshToken;
}

export function getRememberMe(): boolean {
  return rememberMe;
}

export function setRememberMe(value: boolean): void {
  rememberMe = value;
}

/** Store both tokens after login / refresh / verify / reset (opt-in body). */
export function setSessionTokens(tokens: {
  access_token?: string | null;
  refresh_token?: string | null;
  remember_me?: boolean;
}): void {
  if (typeof tokens.remember_me === 'boolean') {
    rememberMe = tokens.remember_me;
  }
  if (tokens.access_token) accessToken = tokens.access_token;
  if (tokens.refresh_token) refreshToken = tokens.refresh_token;

  if (rememberMe && refreshToken) {
    void persistSecureSession({
      accessToken,
      refreshToken,
      rememberMe: true,
    });
    void mirrorWidgetCredentials(accessToken, refreshToken);
  } else {
    void clearSecureSession();
    void clearWidgetCredentials();
  }
}

export function clearSessionTokens(): void {
  accessToken = null;
  refreshToken = null;
  rememberMe = true;
  void clearSecureSession();
  void clearWidgetCredentials();
}

/** Test-only. */
export function _resetSessionTokensForTests(): void {
  accessToken = null;
  refreshToken = null;
  rememberMe = true;
}
