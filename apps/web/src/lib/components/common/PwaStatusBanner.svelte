<script lang="ts">
  import { _ } from 'svelte-i18n';
  import Button from './Button.svelte';
  import { pwaLifecycle } from '$lib/stores/pwaLifecycle';

  function retry(): void {
    if (typeof window === 'undefined') return;
    if (window.navigator.onLine) window.location.reload();
  }
</script>

{#if !$pwaLifecycle.online}
  <aside class="pwa-status pwa-status--offline" role="status" data-testid="pwa-offline-banner">
    <div>
      <strong>{$_('pwa.connection.offline_title')}</strong>
      <span>{$_('pwa.connection.offline_body')}</span>
    </div>
    <Button variant="secondary" size="sm" on:click={retry}>{$_('pwa.connection.retry')}</Button>
  </aside>
{:else if $pwaLifecycle.updateAvailable}
  <aside class="pwa-status" role="status" data-testid="pwa-update-banner">
    <div>
      <strong>{$_('pwa.update.title')}</strong>
      <span>{$_('pwa.update.body')}</span>
    </div>
    <Button variant="secondary" size="sm" on:click={() => pwaLifecycle.activateUpdate()}>
      {$_('pwa.update.cta')}
    </Button>
  </aside>
{/if}

<style>
  .pwa-status {
    position: fixed;
    z-index: 220;
    inset-inline: var(--space-4);
    bottom: calc(5rem + env(safe-area-inset-bottom));
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--space-3);
    max-width: 42rem;
    margin-inline: auto;
    padding: var(--space-3);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    background: var(--color-surface);
    box-shadow: var(--shadow-lg);
  }

  .pwa-status--offline {
    border-color: color-mix(in srgb, var(--color-warning) 45%, var(--color-border));
  }

  .pwa-status div {
    display: grid;
    gap: var(--space-1);
    min-width: 0;
  }

  .pwa-status strong {
    font-size: var(--text-sm);
  }

  .pwa-status span {
    color: var(--color-text-muted);
    font-size: var(--text-xs);
    line-height: 1.4;
  }

  @media (min-width: 768px) {
    .pwa-status {
      bottom: var(--space-4);
    }
  }

  @media (max-width: 360px) {
    .pwa-status {
      align-items: stretch;
      flex-direction: column;
    }
  }
</style>
