/**
 * Service worker registration helpers — dev cleanup + explicit prod registration.
 *
 * SvelteKit auto-registration is disabled in svelte.config.js so dev HMR is not
 * blocked by a stale cache-controlling service worker.
 *
 * Capacitor APKs must not register a service worker: clients.claim() + navigate
 * handling can blank the WebView around the first post-login route change.
 * Older APKs may still have a registration; clear it on boot.
 */

import { isCapacitorBuild } from '$lib/api/platform';

async function unregisterAllServiceWorkers(): Promise<void> {
  if (typeof navigator === 'undefined' || !('serviceWorker' in navigator)) {
    return;
  }
  const registrations = await navigator.serviceWorker.getRegistrations();
  await Promise.all(registrations.map((registration) => registration.unregister()));
  if ('caches' in globalThis) {
    const keys = await caches.keys();
    await Promise.all(keys.map((key) => caches.delete(key)));
  }
}

/** Unregister any SW and clear caches left from a previous dev session. */
export async function cleanupDevServiceWorker(): Promise<void> {
  if (!import.meta.env.DEV) {
    return;
  }
  await unregisterAllServiceWorkers();
}

/**
 * One-time cleanup for Capacitor production WebViews that still have a SW
 * registered from an older APK (pre-#440). Safe to call every boot.
 */
export async function cleanupCapacitorServiceWorker(): Promise<void> {
  if (!isCapacitorBuild() || import.meta.env.DEV) {
    return;
  }
  await unregisterAllServiceWorkers();
}

/** Register the app shell service worker in production browser builds only. */
export async function registerProdServiceWorker(): Promise<void> {
  if (
    !import.meta.env.PROD ||
    isCapacitorBuild() ||
    typeof navigator === 'undefined' ||
    !('serviceWorker' in navigator)
  ) {
    return;
  }
  await navigator.serviceWorker.register('/service-worker.js', {
    type: import.meta.env.DEV ? 'module' : 'classic',
  });
}
