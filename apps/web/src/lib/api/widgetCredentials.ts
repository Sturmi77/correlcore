/**
 * Mirror Capacitor session credentials into a native SharedPreferences store
 * so the Glance widget / WorkManager can call GET /widget/summary.
 *
 * ADR-0006 keeps JWTs out of web localStorage. The native plugin store is an
 * explicit M11 exception for the homescreen widget only (see WIDGET.md).
 */

import { getApiBase } from './apiBase';
import { isCapacitorBuild } from './platform';

type WidgetCredentialsPlugin = {
  set(options: { accessToken: string; apiBase: string }): Promise<void>;
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

/** Persist access token + API base for the Android widget (Capacitor only). */
export async function mirrorWidgetCredentials(accessToken: string | null): Promise<void> {
  if (!isCapacitorBuild()) return;
  const plugin = getNativePlugin();
  if (!plugin) return;

  try {
    if (!accessToken) {
      await plugin.clear();
      return;
    }
    await plugin.set({ accessToken, apiBase: getApiBase() });
  } catch {
    /* Widget sync is best-effort — never block login/logout. */
  }
}

/** Clear native widget credentials (logout / failed refresh). */
export async function clearWidgetCredentials(): Promise<void> {
  await mirrorWidgetCredentials(null);
}

/** Re-mirror current API base when Settings changes the runtime override. */
export async function remirrorWidgetApiBase(accessToken: string | null): Promise<void> {
  if (!accessToken) return;
  await mirrorWidgetCredentials(accessToken);
}
