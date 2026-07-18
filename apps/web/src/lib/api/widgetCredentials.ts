/**
 * Mirror Capacitor session credentials into a native SharedPreferences store
 * so the Glance widget / WorkManager can call GET /widget/summary.
 *
 * ADR-0006 keeps JWTs out of web localStorage. The native plugin store is an
 * explicit M11 exception for the homescreen widget only (see WIDGET.md).
 * Access + refresh are mirrored so WorkManager can rotate after the 15m access TTL.
 */

import { getApiBase } from './apiBase';
import { isCapacitorBuild } from './platform';

type WidgetCredentialsPlugin = {
  set(options: { accessToken: string; refreshToken: string; apiBase: string }): Promise<void>;
  clear(): Promise<void>;
};

function getNativePlugin(): WidgetCredentialsPlugin | null {
  if (typeof window === 'undefined') return null;
  const cap = (
    window as unknown as {
      Capacitor?: { Plugins?: Record<string, WidgetCredentialsPlugin> };
    }
  ).Capacitor;
  return cap?.Plugins?.WidgetCredentials ?? null;
}

/**
 * Persist access + refresh + API base for the Android widget (Capacitor only).
 * Pass null access (or missing refresh) to clear.
 */
export async function mirrorWidgetCredentials(
  accessToken: string | null,
  refreshToken: string | null = null
): Promise<void> {
  if (!isCapacitorBuild()) return;
  const plugin = getNativePlugin();
  if (!plugin) return;

  try {
    if (!accessToken || !refreshToken) {
      await plugin.clear();
      return;
    }
    await plugin.set({
      accessToken,
      refreshToken,
      apiBase: getApiBase(),
    });
  } catch {
    /* Widget sync is best-effort — never block login/logout. */
  }
}

/** Clear native widget credentials (logout / failed refresh). */
export async function clearWidgetCredentials(): Promise<void> {
  await mirrorWidgetCredentials(null, null);
}

/** Re-mirror current tokens when Settings changes the runtime API base. */
export async function remirrorWidgetApiBase(
  accessToken: string | null,
  refreshToken: string | null
): Promise<void> {
  await mirrorWidgetCredentials(accessToken, refreshToken);
}
