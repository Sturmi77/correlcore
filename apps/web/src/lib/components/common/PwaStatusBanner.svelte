<script lang="ts">
  import { _ } from 'svelte-i18n';
  import Button from './Button.svelte';
  import { reconnectSession } from '$lib/stores/auth';
  import { connectivity, isEffectivelyOffline } from '$lib/stores/connectivity';
  import { pwaLifecycle } from '$lib/stores/pwaLifecycle';
  import { scheduleSync, syncOrchestrator } from '$lib/offline/syncOrchestrator';

  let retrying = false;

  $: offline = isEffectivelyOffline($connectivity);
  $: browserOffline = !$connectivity.browserOnline;
  $: serverDown = $connectivity.browserOnline && $connectivity.serverReachable === false;
  $: pendingCount = $syncOrchestrator.pendingCount;
  $: showPending = pendingCount > 0;

  async function retry(): Promise<void> {
    if (typeof window === 'undefined' || retrying) return;
    if (!window.navigator.onLine) return;
    retrying = true;
    try {
      const result = await reconnectSession();
      if (result === 'online') {
        scheduleSync();
      } else if (result === 'anonymous') {
        // Layout guard sends the user to login.
        return;
      }
    } finally {
      retrying = false;
    }
  }
</script>

{#if offline}
  <aside
    class="pwa-status pwa-status--offline"
    role="status"
    data-testid={serverDown ? 'pwa-server-unavailable-banner' : 'pwa-offline-banner'}
  >
    <div>
      <strong>
        {browserOffline
          ? $_('pwa.connection.offline_title')
          : $_('pwa.connection.server_unavailable_title')}
      </strong>
      <span>
        {browserOffline
          ? $_('pwa.connection.offline_body')
          : $_('pwa.connection.server_unavailable_body')}
      </span>
      {#if showPending}
        <span data-testid="pwa-pending-sync">
          {$_('pwa.connection.pending_sync', { values: { count: pendingCount } })}
        </span>
      {/if}
    </div>
    <Button variant="secondary" size="sm" disabled={retrying} on:click={() => void retry()}>
      {$_('pwa.connection.retry')}
    </Button>
  </aside>
{:else if showPending}
  <aside class="pwa-status pwa-status--pending" role="status" data-testid="pwa-pending-sync-banner">
    <div>
      <strong>{$_('pwa.connection.pending_title')}</strong>
      <span data-testid="pwa-pending-sync">
        {$_('pwa.connection.pending_sync', { values: { count: pendingCount } })}
      </span>
    </div>
    <Button variant="secondary" size="sm" on:click={() => scheduleSync()}>
      {$_('pwa.connection.sync_now')}
    </Button>
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

  .pwa-status--pending {
    border-color: color-mix(in srgb, var(--color-accent) 40%, var(--color-border));
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
