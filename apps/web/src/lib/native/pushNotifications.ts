/**
 * Capacitor FCM registration (M11 Sprint 5).
 *
 * No-op for browser / cookie builds. Sideload builds without
 * `google-services.json` fail registration quietly — that is intentional
 * so GitHub/Obtainium APKs stay free of a hard Firebase dependency.
 */

import { isCapacitorBuild } from '$lib/api/platform';
import { registerPushToken, unregisterPushToken } from '$lib/api/devices';

let currentToken: string | null = null;
let listenersAttached = false;

function isNativeCapacitor(): boolean {
  if (!isCapacitorBuild() || typeof window === 'undefined') return false;
  const cap = (
    window as unknown as {
      Capacitor?: { isNativePlatform?: () => boolean };
    }
  ).Capacitor;
  return Boolean(cap?.isNativePlatform?.());
}

async function loadPlugin() {
  return import('@capacitor/push-notifications');
}

async function attachListeners(
  PushNotifications: Awaited<ReturnType<typeof loadPlugin>>['PushNotifications']
): Promise<void> {
  if (listenersAttached) return;
  listenersAttached = true;

  await PushNotifications.addListener('registration', (event) => {
    currentToken = event.value;
    void registerPushToken({
      token: event.value,
      provider: 'fcm',
      platform: 'android',
    }).catch(() => {
      /* best-effort — API may be unreachable offline */
    });
  });

  await PushNotifications.addListener('registrationError', () => {
    /* Missing google-services.json or Play Services — expected on some sideloads */
  });
}

/** Request permission + register FCM after login / hydrate (Capacitor only). */
export async function enablePushNotifications(): Promise<void> {
  if (!isNativeCapacitor()) return;

  try {
    const { PushNotifications } = await loadPlugin();
    await attachListeners(PushNotifications);

    const perm = await PushNotifications.requestPermissions();
    if (perm.receive !== 'granted') return;

    await PushNotifications.register();
  } catch {
    /* Plugin unavailable or Firebase not linked — leave push off */
  }
}

/** Unregister current token on logout (best-effort). */
export async function disablePushNotifications(): Promise<void> {
  const token = currentToken;
  currentToken = null;
  if (!token) return;
  try {
    await unregisterPushToken(token);
  } catch {
    /* ignore */
  }
}
