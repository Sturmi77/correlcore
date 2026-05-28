<script lang="ts">
  import { _ } from 'svelte-i18n';
  import Button from '$lib/components/common/Button.svelte';
  import Panel from '$lib/components/common/Panel.svelte';
</script>

<svelte:head>
  <title>{$_('pwa.offline.title')} - {$_('app.name')}</title>
</svelte:head>

<main class="offline-page">
  <Panel variant="bordered">
    <h1>{$_('pwa.offline.title')}</h1>
    <p>{$_('pwa.offline.body')}</p>
    <Button href="/" variant="primary">{$_('pwa.offline.cta')}</Button>
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
</style>
