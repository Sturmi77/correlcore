<script lang="ts">
  import '../app.css';
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { goto } from '$app/navigation';
  import { isLoading } from 'svelte-i18n';
  import { setupI18n } from '$lib/i18n';
  import { theme } from '$lib/stores/theme';
  import { auth, hydrate } from '$lib/stores/auth';

  // svelte-i18n's `init()` registers the locale dictionary asynchronously
  // (locale files are dynamic imports). We must NOT render any child that
  // calls `$_(...)` before the dictionary is loaded — otherwise the very
  // first format call throws "Cannot format a message without first setting
  // the initial locale", the render pipeline aborts, and the user sees a
  // blank page. The `isLoading` store from svelte-i18n flips to `false`
  // once the active locale is ready; we gate the slot on that.
  setupI18n();

  // Routes that do NOT require authentication.
  // Anything else triggers a redirect to /auth/login when no session exists.
  const PUBLIC_PREFIXES = ['/auth', '/status'];

  function isPublic(pathname: string): boolean {
    return PUBLIC_PREFIXES.some((p) => pathname === p || pathname.startsWith(`${p}/`));
  }

  // Re-sync theme store with persisted value + hydrate auth on mount.
  // The inline bootstrap in app.html already sets data-theme before first
  // paint to avoid a flash of wrong theme; here we mirror it into the store
  // so reactive consumers (toggle button, etc.) start in the correct state.
  onMount(() => {
    const saved = (() => {
      try {
        return localStorage.getItem('moodsync-theme') as 'light' | 'dark' | null;
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
    !isPublic($page.url.pathname)
  ) {
    const next = encodeURIComponent($page.url.pathname + $page.url.search);
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
  {:else if $auth.status === 'loading' && !isPublic($page.url.pathname)}
    <!--
      Auth is still hydrating and the route is protected.
      Render an unobtrusive splash so we don't briefly show protected
      content before the redirect kicks in.
    -->
    <div class="auth-splash" aria-busy="true" aria-live="polite">
      <span class="sr-only">Loading…</span>
    </div>
  {:else}
    <!--
      page-shell: Safe-Area-Padding + max-width + centering (see app.css).
      overflow-y-auto here so only the content scrolls, not the whole viewport.
      Use .bleed-full on child elements (charts, heatmaps) that need full width.
    -->
    <main class="page-shell flex-1 overflow-y-auto">
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
