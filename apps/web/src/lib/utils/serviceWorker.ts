/**
 * Service worker registration helpers — dev cleanup + explicit prod registration.
 *
 * SvelteKit auto-registration is disabled in svelte.config.js so dev HMR is not
 * blocked by a stale cache-controlling service worker.
 */

/** Unregister any SW and clear caches left from a previous dev session. */
export async function cleanupDevServiceWorker(): Promise<void> {
  if (!import.meta.env.DEV || typeof navigator === 'undefined' || !('serviceWorker' in navigator)) {
    return;
  }
  const registrations = await navigator.serviceWorker.getRegistrations();
  await Promise.all(registrations.map((registration) => registration.unregister()));
  if ('caches' in globalThis) {
    const keys = await caches.keys();
    await Promise.all(keys.map((key) => caches.delete(key)));
  }
}

/** Register the app shell service worker in production builds only. */
export async function registerProdServiceWorker(): Promise<void> {
  if (
    !import.meta.env.PROD ||
    typeof navigator === 'undefined' ||
    !('serviceWorker' in navigator)
  ) {
    return;
  }
  await navigator.serviceWorker.register('/service-worker.js', { type: 'module' });
}
