<script lang="ts">
  import '../app.css';
  import { onMount } from 'svelte';
  import { setupI18n } from '$lib/i18n';
  import { theme } from '$lib/stores/theme';

  setupI18n();

  // Apply theme class to <html> on mount (SSR-safe)
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
  });
</script>

<svelte:head>
  <meta name="description" content="Privacy-first mood &amp; habit tracker — understand why some days are good and others are bad." />
</svelte:head>

<!-- Theme wrapper: data-theme drives Skeleton UI + custom CSS vars -->
<div class="h-dvh flex flex-col">
  <slot />
</div>
