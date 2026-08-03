<script lang="ts">
  import { onMount } from 'svelte';
  import { _ } from 'svelte-i18n';
  import Button from '$lib/components/common/Button.svelte';
  import Panel from '$lib/components/common/Panel.svelte';
  import ScreenHeader from '$lib/components/common/ScreenHeader.svelte';
  import { fetchUserConsents, type ConsentListResponse } from '$lib/api/consents';
  import {
    fetchUserPreferences,
    updateUserPreferences,
    type UserPreferencesResponse,
  } from '$lib/api/preferences';
  import { canUseHealthConnectImport } from '$lib/healthConnect/consent';
  import {
    checkHealthConnectPermissions,
    isHealthConnectAvailable,
    isHealthConnectBridgePresent,
    requestHealthConnectPermissions,
  } from '$lib/native/healthConnect';
  import { syncHealthConnectSleep } from '$lib/native/healthConnectSync';

  // Health Connect reads exactly these two data types — nothing else.
  const dataKeys = ['sleep', 'heart_rate'] as const;
  const sectionKeys = ['what', 'why', 'ondevice', 'control'] as const;
  // Foreground sync window: the last 7 days of nights, matching the entries
  // REST API's editable/backdate window (BACKDATE_DAYS_LIMIT) so every
  // imported value can still be edited or cleared like a manual entry.
  const SYNC_WINDOW_DAYS = 7;

  let consents: ConsentListResponse | null = null;
  let preferences: UserPreferencesResponse | null = null;
  let sleepSyncEnabled = true;
  let bridgePresent = false;
  let available = false;
  let granted = false;
  let busy = false;
  let syncing = false;
  let syncMessageKey: string | null = null;

  $: consentGranted = canUseHealthConnectImport(consents);

  async function refresh(): Promise<void> {
    bridgePresent = isHealthConnectBridgePresent();
    if (!bridgePresent) return;
    available = (await isHealthConnectAvailable()).available;
    granted = (await checkHealthConnectPermissions()).granted;
  }

  async function grantAccess(): Promise<void> {
    busy = true;
    try {
      const state = await requestHealthConnectPermissions(consents);
      granted = state.granted;
      available = state.available || available;
    } finally {
      busy = false;
    }
  }

  async function toggleSleepSync(event: Event): Promise<void> {
    const enabled = (event.currentTarget as HTMLInputElement).checked;
    sleepSyncEnabled = enabled;
    try {
      preferences = await updateUserPreferences({ health_connect_sync_sleep_enabled: enabled });
      sleepSyncEnabled = preferences.health_connect_sync_sleep_enabled ?? true;
    } catch {
      // Revert the optimistic toggle on failure.
      sleepSyncEnabled = !enabled;
    }
  }

  async function syncNow(): Promise<void> {
    syncing = true;
    syncMessageKey = null;
    try {
      const end = new Date();
      const start = new Date(end.getTime() - SYNC_WINDOW_DAYS * 24 * 60 * 60 * 1000);
      // Known failures are returned as status codes (never thrown) so the UI
      // can show a specific message instead of a generic "check your connection".
      const result = await syncHealthConnectSleep(consents, {
        start: start.toISOString(),
        end: end.toISOString(),
      });
      syncMessageKey = `health_connect.sync.${result.status}`;
      if (result.status === 'sync_disabled') {
        // The server is authoritative: reflect the disabled toggle locally too.
        sleepSyncEnabled = false;
      }
    } catch {
      // Unexpected throw only — ApiError/NetworkError are mapped inside sync.
      syncMessageKey = 'health_connect.sync.error';
    } finally {
      syncing = false;
    }
  }

  onMount(async () => {
    try {
      consents = await fetchUserConsents();
    } catch {
      consents = null;
    }
    try {
      preferences = await fetchUserPreferences();
      sleepSyncEnabled = preferences.health_connect_sync_sleep_enabled ?? true;
    } catch {
      preferences = null;
    }
    await refresh();
  });
</script>

<svelte:head>
  <title>{$_('health_connect.page_title')} — {$_('app.name')}</title>
</svelte:head>

<div class="hc-page">
  <ScreenHeader
    title={$_('health_connect.page_title')}
    subtitle={$_('health_connect.page_subtitle')}
  />

  <Panel>
    <p class="hc-page__intro">{$_('health_connect.intro')}</p>

    <ul class="hc-page__data" data-testid="health-connect-data-list">
      {#each dataKeys as key}
        <li>{$_(`health_connect.data.${key}`)}</li>
      {/each}
    </ul>
    <p class="hc-page__note">{$_('health_connect.data_note')}</p>

    {#each sectionKeys as key}
      <section class="hc-page__section" data-testid={`health-connect-section-${key}`}>
        <h2>{$_(`health_connect.sections.${key}.heading`)}</h2>
        <p>{$_(`health_connect.sections.${key}.body`)}</p>
      </section>
    {/each}

    <div class="hc-page__status" data-testid="health-connect-status">
      {#if !bridgePresent}
        <p class="hc-page__note">{$_('health_connect.status.android_only')}</p>
      {:else if !consentGranted}
        <p class="hc-page__note">{$_('health_connect.status.needs_consent')}</p>
        <Button href="/settings" variant="secondary" data-testid="health-connect-open-settings">
          {$_('health_connect.actions.open_settings')}
        </Button>
      {:else if !available}
        <p class="hc-page__note">{$_('health_connect.status.unavailable')}</p>
      {:else if granted}
        <p class="hc-page__note" data-testid="health-connect-granted">
          {$_('health_connect.status.granted')}
        </p>
        <Button
          variant="primary"
          disabled={syncing || !sleepSyncEnabled}
          on:click={syncNow}
          data-testid="health-connect-sync"
        >
          {$_('health_connect.actions.sync')}
        </Button>
        {#if syncMessageKey}
          <p class="hc-page__note" role="status" data-testid="health-connect-sync-result">
            {$_(syncMessageKey)}
          </p>
        {/if}
      {:else}
        <Button
          variant="primary"
          disabled={busy}
          on:click={grantAccess}
          data-testid="health-connect-grant"
        >
          {$_('health_connect.actions.grant')}
        </Button>
      {/if}
    </div>

    {#if consentGranted}
      <label class="hc-page__toggle" data-testid="health-connect-sleep-toggle">
        <input type="checkbox" checked={sleepSyncEnabled} on:change={toggleSleepSync} />
        <span>{$_('health_connect.toggle.sleep_sync')}</span>
      </label>
      <p class="hc-page__note">{$_('health_connect.toggle.sleep_sync_hint')}</p>
    {/if}

    <div class="hc-page__actions">
      <Button href="/settings" variant="secondary" data-testid="health-connect-back">
        {$_('health_connect.actions.back')}
      </Button>
    </div>
  </Panel>
</div>

<style>
  .hc-page {
    display: flex;
    flex-direction: column;
    gap: var(--space-4);
    padding: var(--space-4);
    max-width: 48rem;
    margin: 0 auto;
  }

  .hc-page__intro {
    margin: 0 0 var(--space-3);
    color: var(--color-text-muted);
    line-height: 1.6;
  }

  .hc-page__data {
    margin: 0 0 var(--space-2);
    padding-left: var(--space-4);
  }

  .hc-page__note {
    margin: 0 0 var(--space-4);
    color: var(--color-text-muted);
    line-height: 1.6;
  }

  .hc-page__section {
    margin-bottom: var(--space-5);
  }

  .hc-page__section h2 {
    margin: 0 0 var(--space-2);
    font-size: var(--text-lg);
  }

  .hc-page__section p {
    margin: 0;
    color: var(--color-text-muted);
    line-height: 1.6;
    white-space: pre-line;
  }

  .hc-page__status {
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
    margin-bottom: var(--space-4);
  }

  .hc-page__toggle {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    margin-bottom: var(--space-2);
  }

  .hc-page__actions {
    margin-top: var(--space-2);
  }
</style>
