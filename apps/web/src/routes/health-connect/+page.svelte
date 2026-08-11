<script lang="ts">
  import { onMount } from 'svelte';
  import { browser } from '$app/environment';
  import { get } from 'svelte/store';
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
  import { currentUser } from '$lib/stores/auth';
  import { canUseHealthConnectImport } from '$lib/healthConnect/consent';
  import {
    checkHealthConnectPermissions,
    isHealthConnectAvailable,
    isHealthConnectBridgePresent,
    requestHealthConnectPermissions,
  } from '$lib/native/healthConnect';
  import {
    syncHealthConnectSleep,
    type HealthConnectSyncResult,
  } from '$lib/native/healthConnectSync';

  // Health Connect reads exactly these two data types — nothing else.
  const dataKeys = ['sleep', 'heart_rate'] as const;
  const sectionKeys = ['what', 'why', 'ondevice', 'control'] as const;
  // Foreground sync window: the last 7 days of nights, matching the entries
  // REST API's editable/backdate window (BACKDATE_DAYS_LIMIT) so every
  // imported value can still be edited or cleared like a manual entry.
  const SYNC_WINDOW_DAYS = 7;
  // Device-local record of the last successful sync. There is no server field
  // for this in Phase 1 (issue #653 A1, no schema change), so it lives in
  // localStorage — per-device sync feedback, low stakes. Declared in
  // scripts/check-no-token-storage.mjs (ADR-0006): UX timestamp, no auth material.
  // The value is scoped to the account that wrote it, so a shared browser or
  // Android WebView never shows one user another user's sync state (#654 review).
  const LAST_SYNC_KEY = 'cc_hc_last_sync';

  interface StoredLastSync {
    userId: string | null;
    at: string;
  }

  let consents: ConsentListResponse | null = null;
  let preferences: UserPreferencesResponse | null = null;
  let sleepSyncEnabled = true;
  let bridgePresent = false;
  let available = false;
  let granted = false;
  let busy = false;
  let syncing = false;
  let syncResult: HealthConnectSyncResult | null = null;
  let lastSyncAt: string | null = null;
  let lastSyncLoadedFor: string | null | undefined;

  $: consentGranted = canUseHealthConnectImport(consents);
  // Every sync status maps to a health_connect.sync.* copy key.
  $: syncMessageKey = syncResult ? `health_connect.sync.${syncResult.status}` : null;
  // The server processed an import (not merely a disabled toggle) → a real sync
  // ran, so its counts and touched days are worth showing.
  $: syncSummary =
    syncResult?.imported && syncResult.status !== 'sync_disabled' ? syncResult.imported : null;
  // Load (once) the stored timestamp for whoever is authenticated, and reload if
  // the account changes on this device. Runs only when the user id actually
  // changes, so it never clobbers a fresh timestamp set by syncNow().
  $: {
    const uid = $currentUser?.id ?? null;
    if (browser && lastSyncLoadedFor !== uid) {
      lastSyncLoadedFor = uid;
      lastSyncAt = readLastSyncFor(uid);
    }
  }

  function readLastSyncFor(userId: string | null): string | null {
    if (!browser) return null;
    try {
      const raw = localStorage.getItem(LAST_SYNC_KEY);
      if (!raw) return null;
      const parsed = JSON.parse(raw) as StoredLastSync;
      // Only surface a timestamp that belongs to the viewing account.
      return parsed && parsed.userId === userId ? parsed.at : null;
    } catch {
      return null;
    }
  }

  function persistLastSync(userId: string | null, at: string): void {
    if (!browser) return;
    try {
      localStorage.setItem(LAST_SYNC_KEY, JSON.stringify({ userId, at } satisfies StoredLastSync));
    } catch {
      // Best-effort: private mode / disabled storage must not break the sync.
    }
  }

  function formatDateTime(iso: string): string {
    const d = new Date(iso);
    return Number.isNaN(d.getTime()) ? iso : d.toLocaleString();
  }

  function formatDay(isoDate: string): string {
    const d = new Date(`${isoDate}T00:00:00`);
    return Number.isNaN(d.getTime()) ? isoDate : d.toLocaleDateString();
  }

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
    syncResult = null;
    try {
      const actorUserId = get(currentUser)?.id;
      if (!actorUserId) {
        syncResult = { status: 'error_unauthorized' };
        return;
      }
      const end = new Date();
      const start = new Date(end.getTime() - SYNC_WINDOW_DAYS * 24 * 60 * 60 * 1000);
      // Known failures are returned as status codes (never thrown) so the UI
      // can show a specific message instead of a generic "check your connection".
      // Auth guard: native read can outlive a same-tab account switch; without
      // re-checking the actor, import would use the next account's Bearer.
      const result = await syncHealthConnectSleep(
        consents,
        {
          start: start.toISOString(),
          end: end.toISOString(),
        },
        {
          actorUserId,
          currentUserId: () => get(currentUser)?.id,
        }
      );
      syncResult = result;
      // A completed server round-trip (any non-disabled import outcome) counts
      // as "last synced", even when nothing needed writing. Scope it to the
      // current account so it is never shown to a different user on this device.
      if (result.imported && result.status !== 'sync_disabled') {
        lastSyncAt = new Date().toISOString();
        persistLastSync($currentUser?.id ?? null, lastSyncAt);
      }
      if (result.status === 'sync_disabled') {
        // The server is authoritative: reflect the disabled toggle locally too.
        sleepSyncEnabled = false;
      }
    } catch {
      // Unexpected throw only — ApiError/NetworkError are mapped inside sync.
      syncResult = { status: 'error' };
    } finally {
      syncing = false;
    }
  }

  onMount(async () => {
    // lastSyncAt is loaded reactively from $currentUser (see above).
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
        {#if lastSyncAt}
          <p class="hc-page__note" data-testid="health-connect-last-sync">
            {$_('health_connect.sync.last_synced', {
              values: { when: formatDateTime(lastSyncAt) },
            })}
          </p>
        {/if}
        {#if syncMessageKey}
          <p class="hc-page__note" role="status" data-testid="health-connect-sync-result">
            {$_(syncMessageKey)}
          </p>
        {/if}
        {#if syncSummary}
          <div class="hc-page__sync-summary" data-testid="health-connect-sync-summary">
            <p class="hc-page__sync-counts">
              {$_('health_connect.sync.summary', {
                values: {
                  updated: syncSummary.updated,
                  existing: syncSummary.skipped_existing_value,
                  missing: syncSummary.skipped_no_entry,
                },
              })}
            </p>
            {#if syncResult?.dates && syncResult.dates.length > 0}
              <p class="hc-page__sync-days-heading">{$_('health_connect.sync.days_heading')}</p>
              <ul class="hc-page__sync-days" data-testid="health-connect-sync-days">
                {#each syncResult.dates as day (day)}
                  <li>{formatDay(day)}</li>
                {/each}
              </ul>
            {/if}
          </div>
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

  .hc-page__sync-summary {
    margin-bottom: var(--space-4);
    padding: var(--space-3);
    border-radius: var(--radius-lg);
    border: 1px solid oklch(from var(--color-text) l c h / 0.08);
    background: var(--color-surface-offset);
  }

  .hc-page__sync-counts {
    margin: 0 0 var(--space-2);
    line-height: 1.6;
  }

  .hc-page__sync-days-heading {
    margin: 0 0 var(--space-1);
    font-size: var(--text-sm);
    color: var(--color-text-muted);
  }

  .hc-page__sync-days {
    margin: 0;
    padding-left: var(--space-4);
    font-size: var(--text-sm);
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
