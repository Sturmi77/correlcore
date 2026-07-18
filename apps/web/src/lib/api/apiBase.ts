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
  void import('./sessionTokens').then(({ getAccessToken }) =>
    import('./widgetCredentials').then(({ remirrorWidgetApiBase }) =>
      remirrorWidgetApiBase(getAccessToken())
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

/** Test-only. */
export function _resetApiBaseForTests(): void {
  runtimeOverride = null;
}
