<script lang="ts">
  import { onMount } from 'svelte';
  import { _, locale } from 'svelte-i18n';
  import { get } from 'svelte/store';
  import Button from '$lib/components/common/Button.svelte';
  import InlineAlert from '$lib/components/common/InlineAlert.svelte';
  import Panel from '$lib/components/common/Panel.svelte';
  import ScreenHeader from '$lib/components/common/ScreenHeader.svelte';
  import { getConfiguredApiBaseForDisplay, setRuntimeApiBase } from '$lib/api/apiBase';
  import { isCapacitorBuild } from '$lib/api/platform';
  import { currentUser } from '$lib/stores/auth';
  import { pwaInstallStore } from '$lib/stores/pwaInstall';
  import { pwaLifecycle } from '$lib/stores/pwaLifecycle';
  import { isOfflineSyncEnabled, setOfflineSyncEnabled } from '$lib/offline/featureFlag';
  import { scheduleSync, syncOrchestrator } from '$lib/offline/syncOrchestrator';

  let offlineSyncToggle = false;
  const showApiBase = isCapacitorBuild();
  let apiBaseInput = '';
  let apiBaseMessage: string | null = null;
  let apiBaseError: string | null = null;

  onMount(() => {
    pwaLifecycle.initialize();
    offlineSyncToggle = isOfflineSyncEnabled();
    if (showApiBase) {
      apiBaseInput = getConfiguredApiBaseForDisplay();
    }
  });

  function onSaveApiBase() {
    apiBaseMessage = null;
    apiBaseError = null;
    const translate = get(_);
    const trimmed = apiBaseInput.trim();
    if (!trimmed) {
      setRuntimeApiBase(null);
      apiBaseInput = getConfiguredApiBaseForDisplay();
      apiBaseMessage = translate('settings.app.api_base_cleared');
      return;
    }
    try {
      const parsed = new URL(trimmed);
      if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') {
        throw new Error('protocol');
      }
    } catch {
      apiBaseError = translate('settings.app.api_base_invalid');
      return;
    }
    if (!trimmed.replace(/\/+$/, '').endsWith('/api/v1')) {
      apiBaseError = translate('settings.app.api_base_invalid');
      return;
    }
    setRuntimeApiBase(trimmed);
    apiBaseInput = getConfiguredApiBaseForDisplay();
    apiBaseMessage = translate('settings.app.api_base_saved');
  }

  function formatSyncTime(value: string | null): string {
    const translate = get(_);
    if (!value) return translate('settings.app.sync_never');
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return translate('settings.app.sync_never');
    return date.toLocaleString(get(locale) ?? undefined);
  }

  function onOfflineSyncToggle(event: Event) {
    const checked = (event.currentTarget as HTMLInputElement).checked;
    offlineSyncToggle = checked;
    setOfflineSyncEnabled(checked);
    if (checked) scheduleSync();
  }
</script>

<svelte:head>
  <title>{$_('settings.app.title')} - {$_('app.name')}</title>
</svelte:head>

<main class="app-settings screen-stack">
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

  {#if showApiBase}
    <Panel variant="bordered">
      <div class="app-settings__section app-settings__section--stacked">
        <div>
          <h2>{$_('settings.app.api_base_heading')}</h2>
          <p>{$_('settings.app.api_base_body')}</p>
        </div>
        <label class="app-settings__api-base">
          <span>{$_('settings.app.api_base_label')}</span>
          <input
            type="url"
            bind:value={apiBaseInput}
            placeholder={$_('settings.app.api_base_placeholder')}
            data-testid="api-base-input"
            autocomplete="off"
          />
        </label>
        <Button type="button" size="sm" on:click={onSaveApiBase} data-testid="api-base-save">
          {$_('settings.app.api_base_save')}
        </Button>
        {#if apiBaseError}
          <InlineAlert variant="error" message={apiBaseError} />
        {/if}
        {#if apiBaseMessage}
          <InlineAlert variant="success" message={apiBaseMessage} />
        {/if}
      </div>
    </Panel>
  {/if}

  {#if $currentUser?.is_verified}
    <Panel variant="bordered">
      <div class="app-settings__section app-settings__section--stacked">
        <div>
          <h2>{$_('settings.app.offline_sync_heading')}</h2>
          <p>{$_('settings.app.offline_sync_body')}</p>
        </div>
        <label class="app-settings__toggle">
          <span>{$_('settings.app.offline_sync_toggle')}</span>
          <input
            type="checkbox"
            checked={offlineSyncToggle}
            on:change={onOfflineSyncToggle}
            data-testid="offline-sync-toggle"
          />
        </label>
        <dl class="app-settings__sync-meta">
          <div>
            <dt>{$_('settings.app.sync_last_push')}</dt>
            <dd data-testid="sync-last-push">{formatSyncTime($syncOrchestrator.lastPushAt)}</dd>
          </div>
          <div>
            <dt>{$_('settings.app.sync_last_pull')}</dt>
            <dd data-testid="sync-last-pull">{formatSyncTime($syncOrchestrator.lastPullAt)}</dd>
          </div>
          <div>
            <dt>{$_('settings.app.sync_pending')}</dt>
            <dd data-testid="sync-pending-count">{$syncOrchestrator.pendingCount}</dd>
          </div>
        </dl>
        <Button variant="secondary" on:click={() => scheduleSync()}>
          {$_('settings.app.sync_now')}
        </Button>
      </div>
    </Panel>
  {/if}

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
  }

  .app-settings__section {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--space-4);
  }

  .app-settings__section--stacked {
    align-items: stretch;
    flex-direction: column;
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

  .app-settings__toggle {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--space-3);
    font-size: var(--text-sm);
  }

  .app-settings__api-base {
    display: grid;
    gap: var(--space-2);
    font-size: var(--text-sm);
  }

  .app-settings__api-base input {
    width: 100%;
    padding: var(--space-2) var(--space-3);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    background: var(--color-surface);
    color: var(--color-text);
    font: inherit;
  }

  .app-settings__sync-meta {
    display: grid;
    gap: var(--space-3);
    margin: 0;
  }

  .app-settings__sync-meta div {
    display: flex;
    justify-content: space-between;
    gap: var(--space-3);
    font-size: var(--text-sm);
  }

  .app-settings__sync-meta dt {
    margin: 0;
    color: var(--color-text-muted);
  }

  .app-settings__sync-meta dd {
    margin: 0;
    font-weight: 600;
  }

  @media (max-width: 480px) {
    .app-settings__section {
      align-items: stretch;
      flex-direction: column;
    }
  }
</style>
