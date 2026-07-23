/**
 * Capacitor deep-link routing (#447).
 *
 * The homescreen widget's "+ Add entry" button fires
 * `correlcore://entries/new`. The Android manifest declares the scheme and
 * Android delivers the intent to MainActivity, but nothing bridged it into the
 * WebView — so cold and warm launches just opened the shell on whatever route
 * was last active. This module is that bridge.
 *
 * No-op for browser / PWA builds: the custom scheme only exists on Android.
 */

import { isCapacitorBuild } from '$lib/api/platform';
import { buildOpenEntryPath } from '$lib/navigation/openEntry';

/** Custom scheme registered in AndroidManifest.xml. */
const SCHEME = 'correlcore:';

/** Only ISO dates are accepted as a pre-selected entry date. */
const ISO_DATE = /^\d{4}-\d{2}-\d{2}$/;

function isNativeCapacitor(): boolean {
  if (!isCapacitorBuild() || typeof window === 'undefined') return false;
  const cap = (window as unknown as { Capacitor?: { isNativePlatform?: () => boolean } }).Capacitor;
  return Boolean(cap?.isNativePlatform?.());
}

/**
 * Map a `correlcore://` URL to an in-app path.
 *
 * Returns `null` for anything unrecognised so an unexpected intent can never
 * navigate the shell somewhere arbitrary. Exported for tests — it is pure and
 * needs no Capacitor runtime.
 */
export function resolveDeepLink(rawUrl: string): string | null {
  let url: URL;
  try {
    url = new URL(rawUrl);
  } catch {
    return null;
  }
  if (url.protocol !== SCHEME) return null;

  // `correlcore://entries/new` parses with host="entries" and pathname="/new";
  // normalise both halves so the shape stays readable.
  const segments = [url.host, ...url.pathname.split('/')].filter(Boolean);
  const target = segments.join('/');

  if (target !== 'entries/new') return null;

  const date = url.searchParams.get('date');
  const entryDate = date && ISO_DATE.test(date) ? date : undefined;

  // Home owns the entry sheet (GlobalEntrySheet reads ?openEntry=1), so route
  // through it rather than the standalone /entries/new page — that keeps the
  // widget path identical to tapping "+" inside the app.
  return buildOpenEntryPath(entryDate);
}

export interface DeepLinkHandlerOptions {
  /** Navigation callback, normally SvelteKit's `goto`. */
  navigate: (path: string) => void | Promise<unknown>;
}

/**
 * Wire cold-start and warm-resume deep links.
 *
 * Returns a cleanup function; safe to call on non-Capacitor builds, where it
 * does nothing and returns a no-op.
 */
export async function initDeepLinks({ navigate }: DeepLinkHandlerOptions): Promise<() => void> {
  if (!isNativeCapacitor()) return () => {};

  let disposed = false;
  let removeListener: (() => void) | null = null;

  try {
    const { App } = await import('@capacitor/app');

    const handle = (rawUrl: string | undefined | null): void => {
      if (disposed || !rawUrl) return;
      const path = resolveDeepLink(rawUrl);
      if (path) void navigate(path);
    };

    // Warm start: Android delivers onNewIntent while the app is backgrounded.
    const listener = await App.addListener('appUrlOpen', (event) => handle(event.url));
    removeListener = () => void listener.remove();

    // Cold start: the launch intent is already consumed by the time the
    // WebView boots, so appUrlOpen never fires for it.
    const launch = await App.getLaunchUrl();
    handle(launch?.url);
  } catch {
    // Plugin missing or bridge unavailable — leave the shell on its normal
    // route rather than breaking boot.
    return () => {};
  }

  return () => {
    disposed = true;
    removeListener?.();
  };
}
