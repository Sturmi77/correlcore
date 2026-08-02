<script lang="ts">
  import { onMount } from 'svelte';
  import { _ } from 'svelte-i18n';
  import Button from '$lib/components/common/Button.svelte';
  import Panel from '$lib/components/common/Panel.svelte';
  import ScreenHeader from '$lib/components/common/ScreenHeader.svelte';
  import { fetchUserConsents, type ConsentListResponse } from '$lib/api/consents';
  import { canUseHealthConnectImport } from '$lib/healthConnect/consent';
  import {
    checkHealthConnectPermissions,
    isHealthConnectAvailable,
    isHealthConnectBridgePresent,
    requestHealthConnectPermissions,
  } from '$lib/native/healthConnect';

  // Health Connect reads exactly these two data types — nothing else.
  const dataKeys = ['sleep', 'heart_rate'] as const;
  const sectionKeys = ['what', 'why', 'ondevice', 'control'] as const;

  let consents: ConsentListResponse | null = null;
  let bridgePresent = false;
  let available = false;
  let granted = false;
  let busy = false;

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

  onMount(async () => {
    try {
      consents = await fetchUserConsents();
    } catch {
      consents = null;
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

  .hc-page__actions {
    margin-top: var(--space-2);
  }
</style>
