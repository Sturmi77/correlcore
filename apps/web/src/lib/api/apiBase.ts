/**
 * API base URL resolution (browser proxy vs Capacitor absolute URL).
 *
 * Browser / Docker: default `/api/v1` (same-origin → hooks.server.ts proxy).
 * Capacitor: build-time `VITE_API_BASE_URL` (absolute), optional runtime
 * override in localStorage for selfhost testers (not a secret — only the API
 * origin). Tokens never go into localStorage (ADR-0006).
 */

import { isCapacitorBuild } from './platform';

const RUNTIME_STORAGE_KEY = 'correlcore.apiBase';

/** Keep Glance widget API base in sync (dynamic import avoids cycles). */
function syncWidgetApiBase(): void {
  if (!isCapacitorBuild()) return;
  void import('./sessionTokens').then(({ getAccessToken, getRefreshToken }) =>
    import('./widgetCredentials').then(({ remirrorWidgetApiBase }) =>
      remirrorWidgetApiBase(getAccessToken(), getRefreshToken())
    )
  );
}

let runtimeOverride: string | null = null;

function normalizeBase(url: string): string {
  return url.replace(/\/+$/, '');
}

function readStoredBase(): string | null {
  if (typeof window === 'undefined') return null;
  try {
    const raw = localStorage.getItem(RUNTIME_STORAGE_KEY);
    return raw ? normalizeBase(raw) : null;
  } catch {
    return null;
  }
}

/** True when the URL is not an absolute http(s) origin (e.g. `/api/v1`). */
export function isRelativeApiBase(url: string): boolean {
  return !/^https?:\/\//i.test(url.trim());
}

export type ApiBaseValidation =
  { ok: true; normalized: string } | { ok: false; reason: 'empty' | 'invalid' };

/** Validate a user-entered absolute API base (`https://host/api/v1`). */
export function validateAbsoluteApiBase(url: string): ApiBaseValidation {
  const trimmed = url.trim();
  if (!trimmed) return { ok: false, reason: 'empty' };
  try {
    const parsed = new URL(trimmed);
    if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') {
      return { ok: false, reason: 'invalid' };
    }
  } catch {
    return { ok: false, reason: 'invalid' };
  }
  const normalized = normalizeBase(trimmed);
  if (!normalized.endsWith('/api/v1')) {
    return { ok: false, reason: 'invalid' };
  }
  return { ok: true, normalized };
}

/** Current API prefix used by apiFetch (e.g. `/api/v1` or `https://host/api/v1`). */
export function getApiBase(): string {
  if (isCapacitorBuild()) {
    if (runtimeOverride) return runtimeOverride;
    const stored = readStoredBase();
    if (stored) return stored;
  }
  const builtIn = import.meta.env.VITE_API_BASE_URL;
  if (typeof builtIn === 'string' && builtIn.trim()) {
    return normalizeBase(builtIn.trim());
  }
  return '/api/v1';
}

/**
 * Capacitor builds with a relative default need an absolute URL before auth
 * calls can succeed (WebView origin is `https://localhost`).
 */
export function capacitorNeedsApiBaseConfig(): boolean {
  return isCapacitorBuild() && isRelativeApiBase(getApiBase());
}

/**
 * Persist an optional login/register API base override, then ensure the
 * resolved Capacitor API base is absolute.
 *
 * Empty input keeps the current value (build default or prior override).
 */
export function ensureCapacitorApiBaseConfigured(
  input: string
): { ok: true } | { ok: false; errorKey: string } {
  if (!isCapacitorBuild()) return { ok: true };

  const trimmed = input.trim();
  if (trimmed) {
    const validated = validateAbsoluteApiBase(trimmed);
    if (!validated.ok) {
      return { ok: false, errorKey: 'settings.app.api_base_invalid' };
    }
    setRuntimeApiBase(validated.normalized);
    return { ok: true };
  }

  if (isRelativeApiBase(getApiBase())) {
    return { ok: false, errorKey: 'auth.login.error_api_base_required' };
  }
  return { ok: true };
}

/**
 * Set or clear a Capacitor runtime API base (selfhost testers).
 * Persists to localStorage when available. No-op effect on cookie/browser builds
 * unless called while `VITE_CAPACITOR` is set.
 */
export function setRuntimeApiBase(url: string | null): void {
  if (!url || !url.trim()) {
    runtimeOverride = null;
    if (typeof window !== 'undefined') {
      try {
        localStorage.removeItem(RUNTIME_STORAGE_KEY);
      } catch {
        /* ignore */
      }
    }
    syncWidgetApiBase();
    return;
  }
  const normalized = normalizeBase(url.trim());
  runtimeOverride = normalized;
  if (typeof window !== 'undefined') {
    try {
      localStorage.setItem(RUNTIME_STORAGE_KEY, normalized);
    } catch {
      /* private mode — keep in-memory only */
    }
  }
  syncWidgetApiBase();
}

/** Value shown in Settings (Capacitor): stored override or build default. */
export function getConfiguredApiBaseForDisplay(): string {
  return getApiBase();
}

/** Display value for auth forms — blank when only a relative default exists. */
export function getApiBaseInputForDisplay(): string {
  const current = getApiBase();
  return isRelativeApiBase(current) ? '' : current;
}

/** Test-only. */
export function _resetApiBaseForTests(): void {
  runtimeOverride = null;
}
