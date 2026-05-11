/**
 * Central API client — Issue #40.
 *
 * Auth strategy (ADR-0004 + Issue #40 design notes):
 *   - HttpOnly cookies hold the access + refresh tokens.
 *   - This module never reads or writes tokens; the browser handles them.
 *   - On 401 we attempt a single /auth/refresh round-trip and replay the
 *     original request once. Concurrent 401s share the same refresh
 *     promise (single-flight) so we never hammer /refresh in parallel.
 *
 * Privacy:
 *   - We never log request bodies or error payloads. Only HTTP status
 *     and the path go to console for debug — and only when DEV is on.
 *
 * Phase-2 note (M11+):
 *   - In Capacitor (`capacitor://` scheme) third-party cookies to the
 *     backend domain are blocked. When that ground is reached, swap the
 *     `credentials: 'include'` path for an in-memory bearer-token path
 *     behind the same `apiFetch` signature. Backend already returns the
 *     access_token in the JSON body (see TokenResponse).
 */

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? '/api/v1';

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

async function performRefresh(): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/auth/refresh`, {
      method: 'POST',
      credentials: 'include',
      headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
      // Empty body is fine — refresh token comes from the HttpOnly cookie.
      body: '{}',
    });
    return res.ok;
  } catch {
    return false;
  }
}

function refreshAccessToken(): Promise<boolean> {
  if (!refreshInFlight) {
    refreshInFlight = performRefresh().finally(() => {
      // Clear after completion so next 401 can trigger a fresh attempt.
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
  const url = `${API_BASE}${path}`;
  let res: Response;
  try {
    res = await fetch(url, init);
  } catch (err) {
    throw new NetworkError(path, err);
  }

  if (res.status === 401 && !skipAuthRefresh) {
    const refreshed = await refreshAccessToken();
    if (refreshed) {
      try {
        res = await fetch(url, init);
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

  const init: RequestInit = {
    credentials: 'include',
    ...rest,
    headers: finalHeaders,
  };

  if (json !== undefined) {
    finalHeaders.set('Content-Type', 'application/json');
    init.body = JSON.stringify(json);
  }

  const res = await requestWithRefresh(path, init, skipAuthRefresh);

  if (!res.ok) {
    throw await parseError(res, path);
  }

  // 204 No Content — return undefined as T
  if (res.status === 204) {
    return undefined as T;
  }
  return (await res.json()) as T;
}

export async function apiBlob(path: string): Promise<Blob> {
  const headers = new Headers();
  headers.set('Accept', '*/*');
  const res = await requestWithRefresh(path, {
    method: 'GET',
    credentials: 'include',
    headers,
  });
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
