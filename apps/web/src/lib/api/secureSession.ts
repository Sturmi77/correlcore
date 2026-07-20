/**
 * Capacitor persistent session bridge (Issue #453 / ADR-0006).
 *
 * Refresh (+ optional access) live in Android EncryptedSharedPreferences via
 * the SecureSession plugin — never in localStorage / sessionStorage.
 */

import { getApiBase } from './apiBase';
import { isCapacitorBuild } from './platform';

export type SecureSessionPayload = {
  accessToken?: string | null;
  refreshToken: string;
  apiBase?: string | null;
  rememberMe: boolean;
};

/** Native SecureSession.refresh reject codes (Android). */
export type NativeRefreshFailureCode = 'AUTH_REJECTED' | 'TRANSIENT' | 'MISSING' | 'UNKNOWN';

export class NativeRefreshError extends Error {
  readonly code: NativeRefreshFailureCode;

  constructor(code: NativeRefreshFailureCode, message?: string) {
    super(message ?? `native refresh failed: ${code}`);
    this.name = 'NativeRefreshError';
    this.code = code;
  }
}

type SecureSessionPlugin = {
  set(options: {
    accessToken?: string | null;
    refreshToken: string;
    apiBase?: string | null;
    rememberMe: boolean;
  }): Promise<void>;
  get(): Promise<{
    accessToken?: string;
    refreshToken?: string;
    apiBase?: string;
    rememberMe?: boolean;
  }>;
  clear(): Promise<void>;
  /** Native single-flight refresh (shared with Glance WorkManager). */
  refresh?(options: {
    accessToken?: string | null;
    refreshToken?: string | null;
    apiBase?: string | null;
  }): Promise<{
    accessToken?: string;
    refreshToken?: string;
    apiBase?: string;
  }>;
};

function getNativePlugin(): SecureSessionPlugin | null {
  if (typeof window === 'undefined') return null;
  const cap = (
    window as unknown as {
      Capacitor?: { Plugins?: Record<string, SecureSessionPlugin> };
    }
  ).Capacitor;
  return cap?.Plugins?.SecureSession ?? null;
}

function nativeRejectCode(err: unknown): NativeRefreshFailureCode | null {
  if (!err || typeof err !== 'object') return null;
  const code = (err as { code?: unknown }).code;
  if (code === 'AUTH_REJECTED' || code === 'TRANSIENT' || code === 'MISSING') {
    return code;
  }
  return null;
}

/** Persist session when remember_me is on (Capacitor only). */
export async function persistSecureSession(payload: SecureSessionPayload): Promise<void> {
  if (!isCapacitorBuild()) return;
  const plugin = getNativePlugin();
  if (!plugin) return;
  try {
    if (!payload.rememberMe || !payload.refreshToken) {
      await plugin.clear();
      return;
    }
    await plugin.set({
      accessToken: payload.accessToken ?? null,
      refreshToken: payload.refreshToken,
      apiBase: payload.apiBase ?? getApiBase(),
      rememberMe: true,
    });
  } catch {
    /* Best-effort — never block login. */
  }
}

/** Read persisted session for cold-start restore (Capacitor only). */
export async function restoreSecureSession(): Promise<SecureSessionPayload | null> {
  if (!isCapacitorBuild()) return null;
  const plugin = getNativePlugin();
  if (!plugin) return null;
  try {
    const data = await plugin.get();
    if (!data?.refreshToken || data.rememberMe === false) return null;
    return {
      accessToken: data.accessToken ?? null,
      refreshToken: data.refreshToken,
      apiBase: data.apiBase ?? null,
      rememberMe: true,
    };
  } catch {
    return null;
  }
}

/** Clear native secure session (logout / failed refresh / remember off). */
export async function clearSecureSession(): Promise<void> {
  if (!isCapacitorBuild()) return;
  const plugin = getNativePlugin();
  if (!plugin) return;
  try {
    await plugin.clear();
  } catch {
    /* ignore */
  }
}

/**
 * Rotate tokens via the native coordinator when available (Android APK with
 * SecureSession.refresh).
 *
 * - Success → rotated tokens
 * - Known reject codes → throws [NativeRefreshError] (caller must not fall
 *   back to fetch with a stale JWT on TRANSIENT)
 * - Older shells / unknown failure → null so JS can fall back to fetch
 */
export async function nativeRefreshSession(options: {
  refreshToken?: string | null;
  apiBase?: string | null;
}): Promise<{ access_token: string; refresh_token: string } | null> {
  if (!isCapacitorBuild()) return null;
  const plugin = getNativePlugin();
  if (!plugin?.refresh) return null;
  try {
    const data = await plugin.refresh({
      refreshToken: options.refreshToken ?? null,
      apiBase: options.apiBase ?? getApiBase(),
    });
    if (!data?.accessToken || !data?.refreshToken) return null;
    return {
      access_token: data.accessToken,
      refresh_token: data.refreshToken,
    };
  } catch (err) {
    const code = nativeRejectCode(err);
    if (code) {
      throw new NativeRefreshError(code, err instanceof Error ? err.message : undefined);
    }
    return null;
  }
}
