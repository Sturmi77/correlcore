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

import { get } from 'svelte/store';
import { isCapacitorBuild } from '$lib/api/platform';
import { auth } from '$lib/stores/auth';
import { buildOpenEntryPath } from '$lib/navigation/openEntry';

/** Custom scheme registered in AndroidManifest.xml. */
const SCHEME = 'correlcore:';

/** Shape gate for a pre-selected entry date; calendar validity is checked separately. */
const ISO_DATE = /^\d{4}-\d{2}-\d{2}$/;

/**
 * True only for a real calendar day.
 *
 * The shape regex alone accepts `2026-02-30` and `2026-99-99`, which would be
 * forwarded as `as_of` to the dashboard API (rejected there) and then seed the
 * entry form with an unusable date instead of falling back to today.
 */
function isCalendarDate(value: string): boolean {
  if (!ISO_DATE.test(value)) return false;
  const [year, month, day] = value.split('-').map(Number);
  const parsed = new Date(Date.UTC(year, month - 1, day));
  return (
    parsed.getUTCFullYear() === year &&
    parsed.getUTCMonth() === month - 1 &&
    parsed.getUTCDate() === day
  );
}

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
  const entryDate = date && isCalendarDate(date) ? date : undefined;

  // Home owns the entry sheet (GlobalEntrySheet reads ?openEntry=1), so route
  // through it rather than the standalone /entries/new page — that keeps the
  // widget path identical to tapping "+" inside the app.
  return buildOpenEntryPath(entryDate);
}

/**
 * Wrap a resolved path in the login route when the user is signed out.
 *
 * `/` is a public route (landing), so the layout's anonymous guard never fires
 * for `/?openEntry=1` and the pending request would be dropped: the landing
 * login link carries no `next`, and the login handler then defaults to `/`.
 * Routing through login explicitly is what makes the documented signed-out
 * widget flow actually reach the sheet. `safeNext` on the login page accepts
 * in-app paths like this one.
 */
export function loginAwareTarget(path: string, authenticated: boolean): string {
  if (authenticated) return path;
  return `/auth/login?next=${encodeURIComponent(path)}`;
}

/** Resolve once auth leaves `loading`, so cold start does not race hydrate(). */
function whenAuthSettled(): Promise<boolean> {
  const current = get(auth).status;
  if (current !== 'loading') return Promise.resolve(current === 'authenticated');
  return new Promise((resolve) => {
    let settled = false;
    let unsubscribe: (() => void) | null = null;
    const stop = (authenticated: boolean) => {
      settled = true;
      unsubscribe?.();
      resolve(authenticated);
    };
    unsubscribe = auth.subscribe((state) => {
      if (state.status === 'loading') return;
      stop(state.status === 'authenticated');
    });
    // The store may have emitted synchronously before `unsubscribe` was set.
    if (settled) unsubscribe?.();
  });
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
      if (!path) return;
      void whenAuthSettled().then((authenticated) => {
        if (disposed) return;
        void navigate(loginAwareTarget(path, authenticated));
      });
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
