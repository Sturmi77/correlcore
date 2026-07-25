/**
 * Shared error-mapping helpers — Issue #40 follow-up.
 *
 * Each auth route used to define its own `mapError` that translated an
 * unknown error into an i18n key. The bodies were identical except for
 * the status→key table, so they collapse cleanly into one helper.
 *
 * Usage:
 *   const ERRORS: ApiErrorMap = {
 *     401: 'auth.login.error_invalid',
 *     403: 'auth.login.error_unverified',
 *     429: 'auth.login.error_rate_limit',
 *   };
 *   errorKey = mapApiError(err, ERRORS);
 *
 * Call-site status maps win. Unmapped ApiErrors and NetworkErrors get
 * built-in transport/server keys before the generic fallback.
 */

import { ApiError, NetworkError, SessionPersistenceError } from '$lib/api/client';
import { isCapacitorBuild } from '$lib/api/platform';

/** Map of HTTP status code → i18n key. */
export type ApiErrorMap = Record<number, string>;

/** Default fallback i18n key when no specific status mapping matches. */
export const GENERIC_ERROR_KEY = 'error.generic';

/** Built-in keys for transport / infrastructure failures. */
export const NETWORK_ERROR_KEY = 'error.network';
/** Capacitor-specific: absolute API URL + reachability (CORS is auto-allowed). */
export const NETWORK_ERROR_CAPACITOR_KEY = 'error.network_capacitor';
export const UPSTREAM_ERROR_KEY = 'error.upstream';
export const SERVER_ERROR_KEY = 'error.server';
export const VALIDATION_ERROR_KEY = 'error.validation';
/** Credentials accepted but the session cookie never persisted (not a bad password). */
export const SESSION_ERROR_KEY = 'error.session_not_persisted';

function builtInApiErrorKey(status: number): string | null {
  if (status === 502) return UPSTREAM_ERROR_KEY;
  if (status === 422) return VALIDATION_ERROR_KEY;
  if (status >= 500) return SERVER_ERROR_KEY;
  return null;
}

/**
 * Translate an unknown error into an i18n message key.
 *
 * @param err       The thrown value (caught from `await api.*()`).
 * @param statusMap Status-code → i18n-key lookup table.
 * @param fallback  Key returned when no mapping matches. Defaults to
 *                  `GENERIC_ERROR_KEY`.
 */
export function mapApiError(
  err: unknown,
  statusMap: ApiErrorMap,
  fallback: string = GENERIC_ERROR_KEY
): string {
  if (err instanceof SessionPersistenceError) {
    // Never let this fall through to a call-site 401 mapping (→ "wrong
    // password"). The credentials were valid; the cookie did not persist.
    return SESSION_ERROR_KEY;
  }
  if (err instanceof ApiError) {
    if (statusMap[err.status]) {
      return statusMap[err.status];
    }
    return builtInApiErrorKey(err.status) ?? fallback;
  }
  if (err instanceof NetworkError) {
    return isCapacitorBuild() ? NETWORK_ERROR_CAPACITOR_KEY : NETWORK_ERROR_KEY;
  }
  return fallback;
}
