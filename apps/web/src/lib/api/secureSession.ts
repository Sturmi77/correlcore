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
