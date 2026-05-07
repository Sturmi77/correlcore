<script lang="ts">
  import '../app.css';
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { goto } from '$app/navigation';
  import { setupI18n } from '$lib/i18n';
  import { theme } from '$lib/stores/theme';
  import { auth, hydrate } from '$lib/stores/auth';

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

<!-- data-theme on <html> drives CSS variables in app.css (light/dark) -->
<div class="h-dvh flex flex-col">
  {#if $auth.status === 'loading' && !isPublic($page.url.pathname)}
    <!--
      Auth is still hydrating and the route is protected.
      Render an unobtrusive splash so we don't briefly show protected
      content before the redirect kicks in.
    -->
    <div class="auth-splash" aria-busy="true" aria-live="polite">
      <span class="sr-only">Loading…</span>
    </div>
  {:else}
    <slot />
  {/if}
</div>

<style>
  .auth-splash {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .sr-only {
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    white-space: nowrap;
    border: 0;
  }
</style>
