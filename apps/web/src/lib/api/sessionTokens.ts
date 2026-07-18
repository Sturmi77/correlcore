/**
 * In-memory JWT pair for Capacitor (ADR-0006 Phase 2).
 *
 * Never persisted to localStorage / sessionStorage. Cleared on logout and
 * failed refresh. Browser cookie path does not use this module.
 */

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
}

export function clearSessionTokens(): void {
  accessToken = null;
  refreshToken = null;
}

/** Test-only. */
export function _resetSessionTokensForTests(): void {
  clearSessionTokens();
}
