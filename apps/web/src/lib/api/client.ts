/**
 * Central API client — Issue #40 + M11 Sprint 3 (ADR-0006).
 *
 * Auth strategy:
 *   - Browser / PWA: HttpOnly cookies (`credentials: 'include'`).
 *   - Capacitor (`VITE_CAPACITOR=1`): in-memory Bearer access token + refresh
 *     via JSON body `{ refresh_token }` (existing RefreshRequest). No
 *     localStorage / sessionStorage for tokens.
 *
 * On 401 we attempt a single /auth/refresh round-trip and replay the
 * original request once. Concurrent 401s share the same refresh promise.
 *
 * Privacy: we never log request bodies or error payloads.
 */

import { getApiBase } from './apiBase';
import { usesBearerAuth } from './platform';
import {
  clearSessionTokens,
  getAccessToken,
  getRefreshToken,
  setSessionTokens,
} from './sessionTokens';

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly detail: string,
    public readonly path: string
  ) {
    super(`API ${status} on ${path}: ${detail}`);
    this.name = 'ApiError';
  }
}

export class NetworkError extends Error {
  constructor(
    public readonly path: string,
    cause?: unknown
  ) {
    super(`Network error on ${path}`);
    this.name = 'NetworkError';
    if (cause) (this as { cause?: unknown }).cause = cause;
  }
}

interface FetchOptions extends Omit<RequestInit, 'body'> {
  /** JSON body — will be stringified and Content-Type set automatically. */
  json?: unknown;
  /** Skip the auto-refresh-on-401 retry. Used by /auth/refresh itself. */
  skipAuthRefresh?: boolean;
}

// Single-flight refresh: at most one /refresh in flight at any time.
let refreshInFlight: Promise<boolean> | null = null;

function buildAuthInit(headers: Headers, rest: RequestInit = {}): RequestInit {
  const bearer = usesBearerAuth();
  if (bearer) {
    const access = getAccessToken();
    if (access) headers.set('Authorization', `Bearer ${access}`);
  }
  return {
    credentials: bearer ? 'omit' : 'include',
    ...rest,
    headers,
  };
}

async function performRefresh(): Promise<boolean> {
  try {
    const headers = new Headers({
      Accept: 'application/json',
      'Content-Type': 'application/json',
    });
    const bearer = usesBearerAuth();
    const body = bearer ? JSON.stringify({ refresh_token: getRefreshToken() }) : '{}';
    const res = await fetch(
      `${getApiBase()}/auth/refresh${bearer ? '?include_access_token=true' : ''}`,
      {
        method: 'POST',
        credentials: bearer ? 'omit' : 'include',
        headers,
        body,
      }
    );
    if (!res.ok) {
      if (bearer) clearSessionTokens();
      return false;
    }
    if (bearer) {
      const data = (await res.json()) as {
        access_token?: string;
        refresh_token?: string;
      };
      if (!data.access_token) {
        clearSessionTokens();
        return false;
      }
      setSessionTokens(data);
    }
    return true;
  } catch {
    return false;
  }
}

function refreshAccessToken(): Promise<boolean> {
  if (!refreshInFlight) {
    refreshInFlight = performRefresh().finally(() => {
      refreshInFlight = null;
    });
  }
  return refreshInFlight;
}

async function parseError(res: Response, path: string): Promise<ApiError> {
  let detail = res.statusText || 'Request failed';
  try {
    const data = (await res.clone().json()) as { detail?: unknown };
    if (typeof data.detail === 'string') detail = data.detail;
  } catch {
    // Non-JSON body — keep statusText
  }
  return new ApiError(res.status, detail, path);
}

async function requestWithRefresh(path: string, init: RequestInit, skipAuthRefresh = false) {
  const url = `${getApiBase()}${path}`;
  let res: Response;
  try {
    res = await fetch(url, init);
  } catch (err) {
    throw new NetworkError(path, err);
  }

  if (res.status === 401 && !skipAuthRefresh) {
    const refreshed = await refreshAccessToken();
    if (refreshed) {
      // Rebuild Authorization header with rotated access token.
      const headers = new Headers(init.headers);
      const replay = buildAuthInit(headers, { ...init, headers });
      try {
        res = await fetch(url, replay);
      } catch (err) {
        throw new NetworkError(path, err);
      }
    }
  }
  return res;
}

/**
 * Make an authenticated request to the CorrelCore API.
 *
 * @throws ApiError      on non-2xx responses (after the 401 retry)
 * @throws NetworkError  on transport failures (offline, DNS, CORS)
 */
export async function apiFetch<T = unknown>(path: string, options: FetchOptions = {}): Promise<T> {
  const { json, skipAuthRefresh, headers, ...rest } = options;

  const finalHeaders = new Headers(headers);
  finalHeaders.set('Accept', 'application/json');

  if (json !== undefined) {
    finalHeaders.set('Content-Type', 'application/json');
  }

  const init = buildAuthInit(finalHeaders, {
    ...rest,
    ...(json !== undefined ? { body: JSON.stringify(json) } : {}),
  });

  const res = await requestWithRefresh(path, init, skipAuthRefresh);

  if (!res.ok) {
    throw await parseError(res, path);
  }

  if (res.status === 204) {
    return undefined as T;
  }
  return (await res.json()) as T;
}

export async function apiBlob(path: string): Promise<Blob> {
  const headers = new Headers();
  headers.set('Accept', '*/*');
  const init = buildAuthInit(headers, { method: 'GET' });
  const res = await requestWithRefresh(path, init);
  if (!res.ok) {
    throw await parseError(res, path);
  }
  return res.blob();
}

/** Convenience helpers. */
export const api = {
  get: <T = unknown>(path: string, options?: FetchOptions) =>
    apiFetch<T>(path, { ...options, method: 'GET' }),

  post: <T = unknown>(path: string, json?: unknown, options?: FetchOptions) =>
    apiFetch<T>(path, { ...options, method: 'POST', json }),

  patch: <T = unknown>(path: string, json?: unknown, options?: FetchOptions) =>
    apiFetch<T>(path, { ...options, method: 'PATCH', json }),

  put: <T = unknown>(path: string, json?: unknown, options?: FetchOptions) =>
    apiFetch<T>(path, { ...options, method: 'PUT', json }),

  delete: <T = unknown>(path: string, options?: FetchOptions) =>
    apiFetch<T>(path, { ...options, method: 'DELETE' }),
};
