<script lang="ts">
  import '../app.css';
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { goto } from '$app/navigation';
  import { _, isLoading } from 'svelte-i18n';
  import { setupI18n } from '$lib/i18n';
  import { theme } from '$lib/stores/theme';
  import { auth, hydrate, reconnectSession } from '$lib/stores/auth';
  import { syncDevModeFromStorage, devPhase } from '$lib/stores/devMode';
  import { ensureStandaloneLaunchRoute } from '$lib/utils/pwaLaunch';
  import AppNav from '$lib/components/common/AppNav.svelte';
  import CorrelCoreSplash from '$lib/components/common/CorrelCoreSplash.svelte';
  import PullToRefresh from '$lib/components/common/PullToRefresh.svelte';
  import PwaStatusBanner from '$lib/components/common/PwaStatusBanner.svelte';
  import GlobalEntrySheet from '$lib/components/entries/GlobalEntrySheet.svelte';
  import { isPublicRoute, isMarketingLandingView, shouldShowAppNav } from '$lib/navigation/appNav';
  import { entrySheetStore } from '$lib/stores/entrySheet';
  import { pwaLifecycle } from '$lib/stores/pwaLifecycle';
  import { initDeepLinks } from '$lib/native/deepLinks';
  import { initializeSyncOrchestrator, scheduleSync } from '$lib/offline/syncOrchestrator';
  import {
    cleanupCapacitorServiceWorker,
    cleanupDevServiceWorker,
    registerProdServiceWorker,
  } from '$lib/utils/serviceWorker';
  import { SPLASH_MIN_MS } from '$lib/constants/splashTiming';
  import { get } from 'svelte/store';

  let mainContentEl: HTMLElement | null = null;

  // svelte-i18n's `init()` registers the locale dictionary asynchronously
  // (locale files are dynamic imports). We must NOT render any child that
  // calls `$_(...)` before the dictionary is loaded — otherwise the very
  // first format call throws "Cannot format a message without first setting
  // the initial locale", the render pipeline aborts, and the user sees a
  // blank page. The `isLoading` store from svelte-i18n flips to `false`
  // once the active locale is ready; we gate the slot on that.
  setupI18n();

  $: pathname = $page.url?.pathname ?? '/';
  $: searchParams = $page.url?.searchParams;
  $: showAppNav = shouldShowAppNav($auth.status, pathname, searchParams);
  $: marketingLandingView = isMarketingLandingView($auth.status, pathname, searchParams);
  $: pullToRefreshDisabled = $entrySheetStore.open;

  // Brand splash: stay up until max(real boot done, min animation duration).
  // Starts false so the first paint always shows the mark; flips true after
  // SPLASH_MIN_MS (or immediately when prefers-reduced-motion).
  let splashMinElapsed = false;

  $: realBootBlocking = $isLoading || ($auth.status === 'loading' && !isPublicRoute(pathname));
  $: showBrandSplash = realBootBlocking || !splashMinElapsed;

  // Re-sync theme store with persisted value + hydrate auth on mount.
  // The inline bootstrap in app.html already sets data-theme before first
  // paint to avoid a flash of wrong theme; here we mirror it into the store
  // so reactive consumers (toggle button, etc.) start in the correct state.
  onMount(() => {
    const reduceMotion =
      typeof window !== 'undefined' &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const splashTimer = setTimeout(
      () => {
        splashMinElapsed = true;
      },
      reduceMotion ? 0 : SPLASH_MIN_MS
    );

    void cleanupDevServiceWorker();
    void cleanupCapacitorServiceWorker();
    void registerProdServiceWorker();
    syncDevModeFromStorage();
    devPhase.setOnboardingPreviewOpen(false);
    ensureStandaloneLaunchRoute((path) => {
      void goto(path, { replaceState: true });
    });
    pwaLifecycle.initialize();
    const cleanupSync = initializeSyncOrchestrator((listener) => {
      let previousOnline = get(pwaLifecycle).online;
      return pwaLifecycle.subscribe((state) => {
        if (state.online !== previousOnline) {
          previousOnline = state.online;
          listener(state.online);
        }
      });
    });
    const saved = (() => {
      try {
        return localStorage.getItem('correlcore-theme') as 'light' | 'dark' | null;
      } catch {
        return null;
      }
    })();
    if (saved) {
      theme.set(saved);
    }
    void hydrate().then(() => scheduleSync());
    const onBrowserOnline = () => {
      // After a network restore, re-probe the API then drain the outbox.
      void reconnectSession().then((result) => {
        if (result === 'online') scheduleSync();
      });
    };
    window.addEventListener('online', onBrowserOnline);
    // Widget "+ Add entry" → correlcore://entries/new (#447). No-op off Capacitor.
    let cleanupDeepLinks: (() => void) | null = null;
    void initDeepLinks({ navigate: (path) => goto(path) }).then((cleanup) => {
      cleanupDeepLinks = cleanup;
    });
    return () => {
      clearTimeout(splashTimer);
      cleanupSync();
      cleanupDeepLinks?.();
      window.removeEventListener('online', onBrowserOnline);
    };
  });

  // Reactive guard: any time auth or route changes, redirect if needed.
  $: if (
    typeof window !== 'undefined' &&
    $auth.status === 'anonymous' &&
    !isPublicRoute(pathname)
  ) {
    const next = encodeURIComponent(pathname + ($page.url?.search ?? ''));
    void goto(`/auth/login?next=${next}`, { replaceState: true });
  }
</script>

<svelte:head>
  <meta
    name="description"
    content="Privacy-first mood &amp; habit tracker — understand why some days are good and others are bad."
  />
</svelte:head>

<!--
  Outer shell: h-dvh + flex-col so brand splash can fill the viewport.
  Inner <main> uses .page-shell (defined in app.css) which handles:
    - Safe-Area padding via env(safe-area-inset-*)
    - max-width centering (--content-max-width: 480px)
    - scroll container for page content
  Auth/loading states bypass page-shell intentionally (full-viewport splash).
-->
<div class="h-dvh flex flex-col">
  {#if showBrandSplash}
    <!--
      Brand splash while i18n/auth boot OR until the minimum animation window
      elapses (so the mark is not a one-frame flash on fast loads).
    -->
    <CorrelCoreSplash label={$isLoading ? '' : $_('a11y.loading')} />
  {:else if showAppNav}
    <div class="app-frame app-frame--with-nav">
      <a class="skip-link" href="#main-content">{$_('a11y.skip_to_content')}</a>
      <main
        id="main-content"
        class="page-shell page-shell--with-nav flex-1 overflow-y-auto min-h-0"
        bind:this={mainContentEl}
      >
        <PullToRefresh scrollElement={mainContentEl} disabled={pullToRefreshDisabled}>
          <slot />
        </PullToRefresh>
      </main>
      <AppNav />
      <PwaStatusBanner />
      <GlobalEntrySheet />
    </div>
  {:else}
    <!--
      page-shell: Safe-Area-Padding + max-width + centering (see app.css).
      overflow-y-auto here so only the content scrolls, not the whole viewport.
      Use .bleed-full on child elements (charts, heatmaps) that need full width.
      Anonymous marketing `/` uses a wider shell so the split-hero landing fits.
    -->
    <main
      class="page-shell flex-1 overflow-y-auto min-h-0"
      class:page-shell--marketing={marketingLandingView}
    >
      <slot />
    </main>
  {/if}
</div>
