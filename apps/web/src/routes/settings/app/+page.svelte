<script lang="ts">
  import { onMount } from 'svelte';
  import { _ } from 'svelte-i18n';
  import Button from '$lib/components/common/Button.svelte';
  import InlineAlert from '$lib/components/common/InlineAlert.svelte';
  import Panel from '$lib/components/common/Panel.svelte';
  import ScreenHeader from '$lib/components/common/ScreenHeader.svelte';
  import { pwaInstallStore } from '$lib/stores/pwaInstall';
  import { pwaLifecycle } from '$lib/stores/pwaLifecycle';

  onMount(() => pwaLifecycle.initialize());
</script>

<svelte:head>
  <title>{$_('settings.app.title')} - {$_('app.name')}</title>
</svelte:head>

<main class="app-settings">
  <ScreenHeader title={$_('settings.app.title')} subtitle={$_('settings.app.subtitle')} compact>
    <Button slot="actions" href="/settings" variant="ghost" size="sm">
      {$_('settings.app.back_settings')}
    </Button>
  </ScreenHeader>

  <Panel variant="bordered">
    <div class="app-settings__section">
      <div>
        <h2>{$_('settings.app.connection_heading')}</h2>
        <p>
          {$pwaLifecycle.online
            ? $_('settings.app.connection_online')
            : $_('settings.app.connection_offline')}
        </p>
      </div>
      <span
        class:online={$pwaLifecycle.online}
        class="app-settings__status"
        data-testid="connection-status"
      >
        {$pwaLifecycle.online
          ? $_('settings.app.status_online')
          : $_('settings.app.status_offline')}
      </span>
    </div>
  </Panel>

  <Panel variant="bordered">
    <div class="app-settings__section">
      <div>
        <h2>{$_('settings.app.install_heading')}</h2>
        <p>
          {$pwaInstallStore.installed
            ? $_('settings.app.install_installed')
            : $_('settings.app.install_body')}
        </p>
      </div>
      {#if $pwaInstallStore.promptEvent && !$pwaInstallStore.installed}
        <Button variant="primary" on:click={() => void pwaInstallStore.promptInstall()}>
          {$_('pwa.install.cta')}
        </Button>
      {/if}
    </div>
    {#if !$pwaInstallStore.installed && !$pwaInstallStore.promptEvent}
      <InlineAlert variant="info" message={$_('settings.app.install_unavailable')} />
    {/if}
  </Panel>

  <Panel variant="bordered">
    <div class="app-settings__section">
      <div>
        <h2>{$_('settings.app.update_heading')}</h2>
        <p>
          {$pwaLifecycle.updateAvailable
            ? $_('settings.app.update_available')
            : $_('settings.app.update_current')}
        </p>
      </div>
      {#if $pwaLifecycle.updateAvailable}
        <Button variant="primary" on:click={() => pwaLifecycle.activateUpdate()}>
          {$_('pwa.update.cta')}
        </Button>
      {:else}
        <Button
          variant="secondary"
          loading={$pwaLifecycle.checking}
          on:click={() => void pwaLifecycle.checkForUpdate()}
        >
          {$_('settings.app.check_update')}
        </Button>
      {/if}
    </div>
  </Panel>

  <InlineAlert variant="info" message={$_('settings.app.sync_note')} />
</main>

<style>
  .app-settings {
    width: min(100%, 44rem);
    margin: 0 auto;
    padding: var(--space-4);
    display: grid;
    gap: var(--space-4);
  }

  .app-settings__section {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--space-4);
  }

  .app-settings h2,
  .app-settings p {
    margin: 0;
  }

  .app-settings h2 {
    font-size: var(--text-base);
  }

  .app-settings p {
    margin-top: var(--space-1);
    color: var(--color-text-muted);
    font-size: var(--text-sm);
    line-height: 1.5;
  }

  .app-settings__status {
    flex: 0 0 auto;
    color: var(--color-warning);
    font-size: var(--text-sm);
    font-weight: 650;
  }

  .app-settings__status.online {
    color: var(--color-success);
  }

  @media (max-width: 520px) {
    .app-settings__section {
      align-items: stretch;
      flex-direction: column;
    }
  }
</style>
