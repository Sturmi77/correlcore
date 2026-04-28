<script lang="ts">
  import { _ } from 'svelte-i18n';
  import { theme } from '$lib/stores/theme';

  $: currentTheme = $theme;
</script>

<svelte:head>
  <title>{$_('app.name')}</title>
</svelte:head>

<main class="flex-1 flex flex-col items-center justify-center p-6 gap-8">
  <!-- Logo -->
  <div class="flex flex-col items-center gap-4">
    <svg
      aria-label="MoodSync"
      viewBox="0 0 48 48"
      width="64"
      height="64"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      class="text-current"
    >
      <!-- Outer circle: sync ring -->
      <circle cx="24" cy="24" r="20" stroke="currentColor" stroke-width="3" opacity="0.25" />
      <!-- Arc indicating sync direction -->
      <path
        d="M24 4 A20 20 0 0 1 44 24"
        stroke="#01696f"
        stroke-width="3"
        stroke-linecap="round"
      />
      <!-- Inner mood indicator (stylised smile arc) -->
      <path
        d="M16 26 Q24 34 32 26"
        stroke="#01696f"
        stroke-width="2.5"
        stroke-linecap="round"
        fill="none"
      />
      <!-- Eyes -->
      <circle cx="19" cy="20" r="1.5" fill="#01696f" />
      <circle cx="29" cy="20" r="1.5" fill="#01696f" />
    </svg>

    <h1 class="h1 text-center" style="font-size: var(--text-xl)">
      {$_('app.name')}
    </h1>
    <p class="text-surface-600-300-token text-center" style="font-size: var(--text-base)">
      {$_('app.tagline')}
    </p>
  </div>

  <!-- Theme toggle -->
  <div class="flex items-center gap-3">
    <span class="text-sm opacity-60">Theme:</span>
    <button
      class="btn btn-sm variant-ghost-surface"
      on:click={() => theme.toggle()}
      aria-label={currentTheme === 'dark' ? $_('theme.toggle_light') : $_('theme.toggle_dark')}
    >
      {#if currentTheme === 'dark'}
        <!-- Sun icon -->
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <circle cx="12" cy="12" r="5" />
          <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42" />
        </svg>
        <span>Hell</span>
      {:else}
        <!-- Moon icon -->
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
        </svg>
        <span>Dunkel</span>
      {/if}
    </button>
  </div>

  <!-- Status badge -->
  <div class="badge variant-soft-warning text-xs">
    Pre-Alpha — M0 Setup
  </div>
</main>
