/**
 * Tests for the shared mapApiError helper.
 *
 * The helper consolidates four near-identical mapError functions that
 * previously lived in the auth pages. Coverage targets:
 *   - status code in the map → returns the mapped i18n key
 *   - status code NOT in the map → falls back to GENERIC_ERROR_KEY
 *   - non-ApiError exceptions (NetworkError, plain Error, undefined) →
 *     fallback path
 *   - custom fallback key is honoured
 */

import { describe, it, expect } from 'vitest';
import { ApiError, NetworkError } from '$lib/api/client';
import { mapApiError, GENERIC_ERROR_KEY, type ApiErrorMap } from './error';

const MAP: ApiErrorMap = {
  401: 'auth.login.error_invalid',
  403: 'auth.login.error_unverified',
  429: 'auth.login.error_rate_limit',
};

describe('mapApiError', () => {
  it('returns the mapped key for a known ApiError status', () => {
    const err = new ApiError(401, 'Invalid credentials', '/auth/login');
    expect(mapApiError(err, MAP)).toBe('auth.login.error_invalid');
  });

  it('returns the mapped key for status 429 (rate-limit)', () => {
    const err = new ApiError(429, 'Too many requests', '/auth/login');
    expect(mapApiError(err, MAP)).toBe('auth.login.error_rate_limit');
  });

  it('falls back to GENERIC_ERROR_KEY for an unmapped status', () => {
    const err = new ApiError(500, 'Internal', '/auth/login');
    expect(mapApiError(err, MAP)).toBe(GENERIC_ERROR_KEY);
  });

  it('falls back when the error is a NetworkError (transport failure)', () => {
    const err = new NetworkError('/auth/login');
    expect(mapApiError(err, MAP)).toBe(GENERIC_ERROR_KEY);
  });

  it('falls back for plain Error / unknown shapes', () => {
    expect(mapApiError(new Error('boom'), MAP)).toBe(GENERIC_ERROR_KEY);
    expect(mapApiError(undefined, MAP)).toBe(GENERIC_ERROR_KEY);
    expect(mapApiError(null, MAP)).toBe(GENERIC_ERROR_KEY);
    expect(mapApiError('string error', MAP)).toBe(GENERIC_ERROR_KEY);
  });

  it('honours a custom fallback key', () => {
    const err = new ApiError(503, 'Down', '/auth/login');
    expect(mapApiError(err, MAP, 'error.maintenance')).toBe('error.maintenance');
  });

  it('GENERIC_ERROR_KEY is the documented default', () => {
    expect(GENERIC_ERROR_KEY).toBe('error.generic');
  });
});
