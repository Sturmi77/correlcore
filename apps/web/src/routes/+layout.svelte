<script lang="ts">
  import '../app.css';
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { goto } from '$app/navigation';
  import { _, isLoading } from 'svelte-i18n';
  import { setupI18n } from '$lib/i18n';
  import { theme } from '$lib/stores/theme';
  import { auth, hydrate } from '$lib/stores/auth';
  import AppNav from '$lib/components/common/AppNav.svelte';
  import { isPublicRoute, shouldShowAppNav } from '$lib/navigation/appNav';

  // svelte-i18n's `init()` registers the locale dictionary asynchronously
  // (locale files are dynamic imports). We must NOT render any child that
  // calls `$_(...)` before the dictionary is loaded — otherwise the very
  // first format call throws "Cannot format a message without first setting
  // the initial locale", the render pipeline aborts, and the user sees a
  // blank page. The `isLoading` store from svelte-i18n flips to `false`
  // once the active locale is ready; we gate the slot on that.
  setupI18n();

  $: pathname = $page.url.pathname;
  $: showAppNav = shouldShowAppNav($auth.status, pathname);

  // Re-sync theme store with persisted value + hydrate auth on mount.
  // The inline bootstrap in app.html already sets data-theme before first
  // paint to avoid a flash of wrong theme; here we mirror it into the store
  // so reactive consumers (toggle button, etc.) start in the correct state.
  onMount(() => {
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
    void hydrate();
  });

  // Reactive guard: any time auth or route changes, redirect if needed.
  $: if (
    typeof window !== 'undefined' &&
    $auth.status === 'anonymous' &&
    !isPublicRoute(pathname)
  ) {
    const next = encodeURIComponent(pathname + $page.url.search);
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
  Outer shell: h-dvh + flex-col so auth-splash can fill the viewport.
  Inner <main> uses .page-shell (defined in app.css) which handles:
    - Safe-Area padding via env(safe-area-inset-*)
    - max-width centering (--content-max-width: 640px)
    - scroll container for page content
  Auth/loading states bypass page-shell intentionally (full-viewport splash).
-->
<div class="h-dvh flex flex-col">
  {#if $isLoading}
    <!--
      svelte-i18n locale dictionary is still loading. Render a silent
      splash so children that use `$_(...)` do not mount before init.
    -->
    <div class="auth-splash" aria-busy="true" aria-live="polite">
      <span class="sr-only">Loading…</span>
    </div>
  {:else if $auth.status === 'loading' && !isPublicRoute(pathname)}
    <!--
      Auth is still hydrating and the route is protected.
      Render an unobtrusive splash so we don't briefly show protected
      content before the redirect kicks in.
    -->
    <div class="auth-splash" aria-busy="true" aria-live="polite">
      <span class="sr-only">Loading…</span>
    </div>
  {:else if showAppNav}
    <div class="app-frame app-frame--with-nav">
      <a class="skip-link" href="#main-content">{$_('a11y.skip_to_content')}</a>
      <main
        id="main-content"
        class="page-shell page-shell--with-nav flex-1 overflow-y-auto min-h-0"
      >
        <slot />
      </main>
      <AppNav />
    </div>
  {:else}
    <!--
      page-shell: Safe-Area-Padding + max-width + centering (see app.css).
      overflow-y-auto here so only the content scrolls, not the whole viewport.
      Use .bleed-full on child elements (charts, heatmaps) that need full width.
    -->
    <main class="page-shell flex-1 overflow-y-auto min-h-0">
      <slot />
    </main>
  {/if}
</div>

<style>
  .auth-splash {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
  }
</style>
