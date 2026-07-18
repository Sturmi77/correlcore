/**
 * Capacitor FCM registration (M11 Sprint 5).
 *
 * No-op for browser / cookie builds. Sideload builds without
 * `google-services.json` must never call PushNotifications.register() —
 * that hits FirebaseMessaging without FirebaseApp and kills the process
 * (Capacitor Bridge rethrows on the main thread; JS try/catch cannot catch it).
 *
 * Availability is gated by the native PushAvailability plugin
 * (BuildConfig.FCM_ENABLED from the same google-services.json check).
 */

import { isCapacitorBuild } from '$lib/api/platform';
import { registerPushToken, unregisterPushToken } from '$lib/api/devices';

let currentToken: string | null = null;
let listenersAttached = false;

type PushAvailabilityPlugin = {
  isAvailable(): Promise<{ available: boolean }>;
};

function isNativeCapacitor(): boolean {
  if (!isCapacitorBuild() || typeof window === 'undefined') return false;
  const cap = (
    window as unknown as {
      Capacitor?: { isNativePlatform?: () => boolean };
    }
  ).Capacitor;
  return Boolean(cap?.isNativePlatform?.());
}

function getPushAvailabilityPlugin(): PushAvailabilityPlugin | null {
  if (typeof window === 'undefined') return null;
  const cap = (
    window as unknown as {
      Capacitor?: { Plugins?: Record<string, PushAvailabilityPlugin> };
    }
  ).Capacitor;
  return cap?.Plugins?.PushAvailability ?? null;
}

/** True only when this APK was built with Firebase wired. */
export async function isPushAvailable(): Promise<boolean> {
  if (!isNativeCapacitor()) return false;
  const plugin = getPushAvailabilityPlugin();
  if (!plugin) {
    // Plugin missing → treat as unavailable (safer than crashing on register).
    return false;
  }
  try {
    const result = await plugin.isAvailable();
    return Boolean(result?.available);
  } catch {
    return false;
  }
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
    /* Play Services missing / token fetch failed — leave push off */
  });
}

/** Request permission + register FCM after login / hydrate (Capacitor only). */
export async function enablePushNotifications(): Promise<void> {
  if (!isNativeCapacitor()) return;

  // Must run before PushNotifications.register() — see file header.
  if (!(await isPushAvailable())) return;

  try {
    const { PushNotifications } = await loadPlugin();
    await attachListeners(PushNotifications);

    const perm = await PushNotifications.requestPermissions();
    if (perm.receive !== 'granted') return;

    await PushNotifications.register();
  } catch {
    /* Plugin unavailable — leave push off */
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

/** Test-only: reset module state between Vitest cases. */
export function _resetPushNotificationsForTests(): void {
  currentToken = null;
  listenersAttached = false;
}
