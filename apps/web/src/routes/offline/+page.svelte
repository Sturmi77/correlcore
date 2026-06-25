<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { _ } from 'svelte-i18n';
  import Button from '$lib/components/common/Button.svelte';
  import Panel from '$lib/components/common/Panel.svelte';
  import { pwaLifecycle } from '$lib/stores/pwaLifecycle';

  onMount(() => pwaLifecycle.initialize());

  function retry(): void {
    if (typeof window === 'undefined') return;
    if (window.navigator.onLine) {
      void goto('/');
      return;
    }
    window.location.reload();
  }
</script>

<svelte:head>
  <title>{$_('pwa.offline.title')} - {$_('app.name')}</title>
</svelte:head>

<main class="offline-page">
  <Panel variant="bordered">
    <h1>{$_('pwa.offline.title')}</h1>
    <p>{$_('pwa.offline.body')}</p>
    <p class="offline-page__status" class:online={$pwaLifecycle.online} role="status">
      {$pwaLifecycle.online ? $_('pwa.offline.restored') : $_('pwa.offline.still_offline')}
    </p>
    <Button variant="primary" on:click={retry}>
      {$pwaLifecycle.online ? $_('pwa.offline.cta') : $_('pwa.offline.retry')}
    </Button>
  </Panel>
</main>

<style>
  .offline-page {
    width: min(100%, 34rem);
    min-height: 70dvh;
    margin: 0 auto;
    padding: var(--space-6) var(--space-4);
    display: grid;
    place-items: center;
  }

  .offline-page h1,
  .offline-page p {
    margin: 0 0 var(--space-3);
  }

  .offline-page__status {
    color: var(--color-warning);
    font-size: var(--text-sm);
    font-weight: 650;
  }

  .offline-page__status.online {
    color: var(--color-success);
  }
</style>
