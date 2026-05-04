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
 * Anything that isn't an `ApiError` (NetworkError, programmer errors,
 * unknown shapes) falls back to `'error.generic'`. This keeps user-facing
 * copy safe even when an unexpected exception bubbles up.
 */

import { ApiError } from '$lib/api/client';

/** Map of HTTP status code → i18n key. */
export type ApiErrorMap = Record<number, string>;

/** Default fallback i18n key when no specific status mapping matches. */
export const GENERIC_ERROR_KEY = 'error.generic';

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
  if (err instanceof ApiError && statusMap[err.status]) {
    return statusMap[err.status];
  }
  return fallback;
}
