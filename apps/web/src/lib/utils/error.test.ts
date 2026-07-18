/**
 * Tests for the shared mapApiError helper.
 *
 * The helper consolidates four near-identical mapError functions that
 * previously lived in the auth pages. Coverage targets:
 *   - status code in the map → returns the mapped i18n key
 *   - NetworkError → error.network
 *   - unmapped 502 / 5xx / 422 → built-in infrastructure keys
 *   - other unmapped statuses / plain errors → GENERIC_ERROR_KEY
 *   - custom fallback key is honoured
 */

import { describe, it, expect } from 'vitest';
import { ApiError, NetworkError } from '$lib/api/client';
import {
  mapApiError,
  GENERIC_ERROR_KEY,
  NETWORK_ERROR_KEY,
  UPSTREAM_ERROR_KEY,
  SERVER_ERROR_KEY,
  VALIDATION_ERROR_KEY,
  type ApiErrorMap,
} from './error';

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

  it('maps NetworkError to NETWORK_ERROR_KEY', () => {
    const err = new NetworkError('/auth/login');
    expect(mapApiError(err, MAP)).toBe(NETWORK_ERROR_KEY);
  });

  it('maps unmapped 502 to UPSTREAM_ERROR_KEY', () => {
    const err = new ApiError(502, 'Upstream API unreachable', '/auth/login');
    expect(mapApiError(err, MAP)).toBe(UPSTREAM_ERROR_KEY);
  });

  it('maps unmapped 5xx to SERVER_ERROR_KEY', () => {
    const err = new ApiError(500, 'Internal', '/auth/login');
    expect(mapApiError(err, MAP)).toBe(SERVER_ERROR_KEY);
  });

  it('maps unmapped 422 to VALIDATION_ERROR_KEY', () => {
    const err = new ApiError(422, 'Validation failed', '/auth/login');
    expect(mapApiError(err, MAP)).toBe(VALIDATION_ERROR_KEY);
  });

  it('lets the call-site map override built-in 422 handling', () => {
    const err = new ApiError(422, 'weak', '/auth/register');
    expect(mapApiError(err, { 422: 'auth.register.error_weak_password' })).toBe(
      'auth.register.error_weak_password'
    );
  });

  it('falls back for unmapped client errors (e.g. 404)', () => {
    const err = new ApiError(404, 'Missing', '/auth/login');
    expect(mapApiError(err, MAP)).toBe(GENERIC_ERROR_KEY);
  });

  it('falls back for plain Error / unknown shapes', () => {
    expect(mapApiError(new Error('boom'), MAP)).toBe(GENERIC_ERROR_KEY);
    expect(mapApiError(undefined, MAP)).toBe(GENERIC_ERROR_KEY);
    expect(mapApiError(null, MAP)).toBe(GENERIC_ERROR_KEY);
    expect(mapApiError('string error', MAP)).toBe(GENERIC_ERROR_KEY);
  });

  it('honours a custom fallback key for unmapped client statuses', () => {
    const err = new ApiError(404, 'Missing', '/auth/login');
    expect(mapApiError(err, MAP, 'error.maintenance')).toBe('error.maintenance');
  });

  it('GENERIC_ERROR_KEY is the documented default', () => {
    expect(GENERIC_ERROR_KEY).toBe('error.generic');
  });
});
