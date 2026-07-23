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
import { NativeRefreshError, nativeRefreshSession } from './secureSession';
import { notifySessionExpired } from './sessionExpired';
import {
  clearSessionTokens,
  getAccessToken,
  getRefreshToken,
  setSessionTokens,
  syncSessionTokensFromNative,
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

/** Strip userinfo from absolute URLs so passwords never land in Error.message / UI. */
export function redactUrlCredentials(url: string): string {
  try {
    const parsed = new URL(url);
    if (!parsed.username && !parsed.password) return url;
    parsed.username = '';
    parsed.password = '';
    return parsed.toString();
  } catch {
    // Relative bases (/api/v1) or malformed — scrub embedded userinfo heuristically.
    return url.replace(/\/\/[^/@\s]+@/g, '//***@');
  }
}

export class NetworkError extends Error {
  public readonly path: string;
  /** Resolved API base at failure time (credentials redacted for display). */
  public readonly apiBase?: string;

  constructor(path: string, cause?: unknown, apiBase?: string) {
    const safeBase = apiBase ? redactUrlCredentials(apiBase) : undefined;
    const causeMsg = cause instanceof Error ? cause.message : '';
    const baseHint = safeBase ? ` base=${safeBase}` : '';
    super(
      causeMsg
        ? `Network error on ${path}${baseHint}: ${causeMsg}`
        : `Network error on ${path}${baseHint}`
    );
    this.name = 'NetworkError';
    this.path = path;
    this.apiBase = safeBase;
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
let refreshInFlight: Promise<RefreshOutcome> | null = null;

/** Outcome of an access-token refresh attempt. */
export type RefreshOutcome = 'success' | 'rejected' | 'transient' | 'unavailable';

function buildAuthInit(headers: Headers, rest: RequestInit = {}): RequestInit {
  const bearer = usesBearerAuth();
  if (bearer) {
    const access = getAccessToken();
    if (access) headers.set('Authorization', `Bearer ${access}`);
  }
  // credentials/headers must win over `rest` — callers must not accidentally
  // re-enable cookie credentials on the Capacitor Bearer path.
  return {
    ...rest,
    credentials: bearer ? 'omit' : 'include',
    headers,
  };
}

async function fetchRefreshOnce(): Promise<boolean> {
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
  if (!res.ok) return false;
  if (bearer) {
    const data = (await res.json()) as {
      access_token?: string;
      refresh_token?: string;
    };
    if (!data.access_token) return false;
    setSessionTokens(data);
  }
  return true;
}

async function performRefresh(): Promise<RefreshOutcome> {
  try {
    const bearer = usesBearerAuth();
    if (bearer) {
      // Prefer native coordinator (same lock as Glance WorkManager).
      try {
        const native = await nativeRefreshSession({
          refreshToken: getRefreshToken(),
          apiBase: getApiBase(),
        });
        if (native) {
          setSessionTokens(native);
          return 'success';
        }
      } catch (err) {
        if (err instanceof NativeRefreshError) {
          if (err.code === 'TRANSIENT') {
            // Keep JWTs; do not POST a possibly-stale refresh token via fetch
            // (replay → revoke_all). Caller will surface the original 401.
            return 'transient';
          }
          // AUTH_REJECTED / MISSING / UNKNOWN with a coded reject — clear.
          clearSessionTokens();
          return 'rejected';
        }
        throw err;
      }
      // Older APK / plugin missing: adopt tokens the widget may already have.
      await syncSessionTokensFromNative();
    }

    if (await fetchRefreshOnce()) return 'success';

    if (bearer) {
      // Widget may have won a race and dual-written newer tokens — retry once.
      const synced = await syncSessionTokensFromNative();
      if (synced && (await fetchRefreshOnce())) return 'success';
      clearSessionTokens();
    }
    return 'rejected';
  } catch {
    // Transport failure during refresh — keep the local session so offline
    // mode can continue; do not treat this as credential rejection.
    return 'unavailable';
  }
}

function refreshAccessToken(): Promise<RefreshOutcome> {
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
  const apiBase = getApiBase();
  const url = `${apiBase}${path}`;
  let res: Response;
  try {
    res = await fetch(url, init);
  } catch (err) {
    throw new NetworkError(path, err, apiBase);
  }

  if (res.status === 401 && !skipAuthRefresh) {
    const outcome = await refreshAccessToken();
    if (outcome === 'success') {
      // Rebuild Authorization header with rotated access token.
      const headers = new Headers(init.headers);
      const replay = buildAuthInit(headers, { ...init, headers });
      try {
        res = await fetch(url, replay);
      } catch (err) {
        throw new NetworkError(path, err, apiBase);
      }
    } else if (outcome === 'rejected') {
      // Definitive credential failure — force login via the auth store.
      notifySessionExpired();
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
