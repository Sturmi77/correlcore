<script lang="ts">
  import { page } from '$app/stores';
  import { _ } from 'svelte-i18n';
</script>

<svelte:head>
  <title>Fehler — CorrelCore</title>
</svelte:head>

<main class="flex-1 flex flex-col items-center justify-center p-6 gap-4">
  <h1 class="h2">{$page.status}</h1>
  <p>{$page.error?.message ?? $_('error.generic')}</p>
  <a href="/" class="btn variant-ghost-primary">Zurück zur Startseite</a>
</main>
