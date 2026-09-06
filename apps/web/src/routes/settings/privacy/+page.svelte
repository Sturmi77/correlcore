<script lang="ts">
  import { onMount } from 'svelte';
  import { _, locale } from 'svelte-i18n';
  import { goto } from '$app/navigation';
  import { auth, logout } from '$lib/stores/auth';
  import Button from '$lib/components/common/Button.svelte';
  import IconButton from '$lib/components/common/IconButton.svelte';
  import InlineAlert from '$lib/components/common/InlineAlert.svelte';
  import Panel from '$lib/components/common/Panel.svelte';
  import ScreenHeader from '$lib/components/common/ScreenHeader.svelte';
  import SettingsCategoryBar from '$lib/components/settings/SettingsCategoryBar.svelte';
  import { ApiError } from '$lib/api/client';
  import { deleteAccount } from '$lib/api/user';
  import {
    fetchUserConsents,
    HEALTH_CONNECT_CONSENT_TYPE,
    HEALTH_CONNECT_CONSENT_VERSION,
    recordUserConsent,
    revokeUserConsent,
    type ConsentListResponse,
  } from '$lib/api/consents';
  import { getHealthConnectConsentStatus } from '$lib/healthConnect/consent';
  import { registerPageRefresh } from '$lib/stores/pageRefresh';

  let deleteDialogOpen = false;
  let deletePassword = '';
  let deleteBusy = false;
  let deleteError = '';
  let consents: ConsentListResponse | null = null;
  let consentsBusy = false;
  let consentsError = '';
  let healthConnectGrantChecked = false;

  $: healthConnectConsent = getHealthConnectConsentStatus(consents);
  $: healthConnectGranted = healthConnectConsent?.granted === true;
  $: if (!consentsBusy && !healthConnectGranted) {
    healthConnectGrantChecked = false;
  }

  function formatConsentTimestamp(iso: string | null | undefined): string {
    if (!iso) return '';
    return new Date(iso).toLocaleString($locale ?? undefined);
  }

  async function loadConsents(): Promise<void> {
    if ($auth.status !== 'authenticated') return;
    try {
      consents = await fetchUserConsents();
    } catch (err) {
      consentsError =
        err instanceof Error ? err.message : $_('settings.privacy.health_connect.error');
    }
  }

  async function grantHealthConnectConsent(): Promise<void> {
    if (!healthConnectGrantChecked) return;
    consentsBusy = true;
    consentsError = '';
    try {
      await recordUserConsent({
        type: HEALTH_CONNECT_CONSENT_TYPE,
        version: HEALTH_CONNECT_CONSENT_VERSION,
        granted: true,
      });
      consents = await fetchUserConsents();
    } catch (err) {
      consentsError =
        err instanceof Error ? err.message : $_('settings.privacy.health_connect.error');
    } finally {
      consentsBusy = false;
    }
  }

  async function revokeHealthConnectConsent(): Promise<void> {
    consentsBusy = true;
    consentsError = '';
    try {
      await revokeUserConsent(HEALTH_CONNECT_CONSENT_TYPE);
      healthConnectGrantChecked = false;
      consents = await fetchUserConsents();
    } catch (err) {
      consentsError =
        err instanceof Error ? err.message : $_('settings.privacy.health_connect.error');
    } finally {
      consentsBusy = false;
    }
  }

  async function handleLogout(): Promise<void> {
    await logout();
    await goto('/', { replaceState: true });
  }

  function openDeleteDialog(): void {
    deletePassword = '';
    deleteError = '';
    deleteDialogOpen = true;
  }

  function closeDeleteDialog(): void {
    if (deleteBusy) return;
    deleteDialogOpen = false;
    deletePassword = '';
    deleteError = '';
  }

  async function confirmDeleteAccount(): Promise<void> {
    if (!deletePassword.trim()) return;
    deleteBusy = true;
    deleteError = '';
    try {
      await deleteAccount({ password: deletePassword });
      await logout();
      await goto('/', { replaceState: true });
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        deleteError = $_('settings.privacy.delete_invalid_password');
      } else {
        deleteError = err instanceof Error ? err.message : $_('settings.privacy.delete_error');
      }
    } finally {
      deleteBusy = false;
    }
  }

  onMount(() => {
    void loadConsents();
    return registerPageRefresh(async () => {
      await loadConsents();
    });
  });
</script>

<svelte:head>
  <title>{$_('settings.groups.privacy.title')} - {$_('app.name')}</title>
</svelte:head>

<main class="privacy-settings screen-stack">
  <ScreenHeader
    title={$_('settings.groups.privacy.title')}
    subtitle={$_('settings.groups.privacy.subtitle')}
    compact
    back={{ href: '/settings', label: $_('nav.settings') }}
  />
  <SettingsCategoryBar />

  {#if $auth.status !== 'authenticated'}
    <Panel variant="bordered">
      <p>{$_('settings.auth_required')}</p>
      <Button href="/auth/login" variant="primary" size="sm">{$_('auth.login.submit')}</Button>
    </Panel>
  {:else}
    <Panel variant="bordered">
      <div class="privacy-settings__head">
        <h2>{$_('settings.privacy.heading')}</h2>
        <p>{$_('settings.privacy.body')}</p>
      </div>
      <p class="privacy-settings__note">{$_('settings.privacy.policy_body')}</p>

      <div class="privacy-settings__consent-block" data-testid="settings-health-connect-consent">
        <h3 class="privacy-settings__consent-heading">
          {$_('settings.privacy.health_connect.heading')}
        </h3>
        <p class="privacy-settings__consent-body">{$_('settings.privacy.health_connect.body')}</p>
        <p class="privacy-settings__consent-scope">{$_('settings.privacy.health_connect.scope')}</p>
        <p class="privacy-settings__consent-scope" data-testid="health-connect-deferred-note">
          {$_('settings.privacy.health_connect.deferred_note')}
        </p>
        <div class="privacy-settings__actions">
          <Button href="/health-connect" variant="secondary" data-testid="health-connect-open-sync">
            {$_('settings.privacy.health_connect.manage_action')}
          </Button>
        </div>
        {#if healthConnectGranted && healthConnectConsent?.updated_at}
          <p
            class="privacy-settings__consent-timestamp"
            data-testid="health-connect-consent-timestamp"
          >
            {$_('settings.privacy.health_connect.granted_at', {
              values: { timestamp: formatConsentTimestamp(healthConnectConsent.updated_at) },
            })}
          </p>
        {/if}
        {#if !healthConnectGranted}
          <label class="privacy-settings__toggle-label">
            <input
              type="checkbox"
              class="privacy-settings__toggle"
              bind:checked={healthConnectGrantChecked}
              disabled={consentsBusy}
              data-testid="health-connect-consent-checkbox"
            />
            <span>{$_('settings.privacy.health_connect.grant_label')}</span>
          </label>
          <div class="privacy-settings__actions">
            <Button
              variant="secondary"
              type="button"
              data-testid="health-connect-consent-grant"
              disabled={consentsBusy || !healthConnectGrantChecked}
              on:click={() => void grantHealthConnectConsent()}
            >
              {$_('settings.privacy.health_connect.grant_action')}
            </Button>
          </div>
        {:else}
          <div class="privacy-settings__actions">
            <Button
              variant="danger"
              type="button"
              data-testid="health-connect-consent-revoke"
              disabled={consentsBusy}
              on:click={() => void revokeHealthConnectConsent()}
            >
              {$_('settings.privacy.health_connect.revoke_action')}
            </Button>
          </div>
        {/if}
        {#if consentsError}
          <InlineAlert variant="error" message={consentsError} />
        {/if}
      </div>

      <div class="privacy-settings__actions">
        <Button href="/privacy" variant="secondary" data-testid="settings-privacy-policy">
          {$_('settings.privacy.policy_link')}
        </Button>
      </div>
    </Panel>

    <Panel variant="bordered">
      <div class="privacy-settings__head">
        <h2>{$_('settings.account.heading')}</h2>
        <p>{$_('settings.account.body')}</p>
      </div>
      <div class="privacy-settings__actions">
        <Button variant="ghost" data-testid="settings-logout" on:click={() => void handleLogout()}>
          {$_('auth.logout.label')}
        </Button>
        <Button
          variant="danger"
          type="button"
          data-testid="settings-delete-account"
          on:click={openDeleteDialog}
        >
          {$_('settings.privacy.delete_action')}
        </Button>
      </div>
    </Panel>
  {/if}
</main>

{#if deleteDialogOpen}
  <div
    class="privacy-settings__modal-backdrop"
    role="presentation"
    data-testid="settings-delete-backdrop"
    on:click={closeDeleteDialog}
  >
    <dialog
      open
      class="privacy-settings__modal"
      aria-modal="true"
      aria-labelledby="delete-account-title"
      data-testid="settings-delete-dialog"
      on:click|stopPropagation
    >
      <div class="privacy-settings__modal-head">
        <h2 id="delete-account-title">{$_('settings.privacy.delete_title')}</h2>
        <IconButton
          type="button"
          ariaLabel={$_('settings.privacy.delete_cancel')}
          title={$_('settings.privacy.delete_cancel')}
          on:click={closeDeleteDialog}
        >
          x
        </IconButton>
      </div>
      <div class="privacy-settings__modal-body">
        <p>{$_('settings.privacy.delete_body')}</p>
        <label class="privacy-settings__field">
          <span>{$_('settings.privacy.delete_password')}</span>
          <input
            type="password"
            autocomplete="current-password"
            bind:value={deletePassword}
            data-testid="settings-delete-password"
          />
        </label>
        {#if deleteError}
          <InlineAlert variant="error" message={deleteError} />
        {/if}
        <div class="privacy-settings__actions">
          <Button variant="ghost" type="button" on:click={closeDeleteDialog} disabled={deleteBusy}>
            {$_('settings.privacy.delete_cancel')}
          </Button>
          <Button
            variant="danger"
            type="button"
            loading={deleteBusy}
            disabled={deleteBusy || !deletePassword.trim()}
            data-testid="settings-delete-confirm"
            on:click={() => void confirmDeleteAccount()}
          >
            {deleteBusy
              ? $_('settings.privacy.delete_busy')
              : $_('settings.privacy.delete_confirm')}
          </Button>
        </div>
      </div>
    </dialog>
  </div>
{/if}

<style>
  .privacy-settings {
    width: min(100%, 46rem);
    margin: 0 auto;
  }

  .privacy-settings__head h2 {
    margin: 0;
    font-size: var(--text-lg, 1.125rem);
  }

  .privacy-settings__head p {
    margin: var(--space-1) 0 0;
    color: var(--color-text-muted);
    line-height: 1.5;
  }

  .privacy-settings__note {
    margin: var(--space-2) 0 0;
    color: var(--color-text-muted);
    line-height: 1.5;
  }

  .privacy-settings__consent-block {
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
    margin-top: var(--space-3);
    padding: var(--space-3);
    border-radius: var(--radius-sm);
    border: 1px solid var(--color-border-chart);
    background: var(--color-surface);
  }

  .privacy-settings__consent-heading {
    margin: 0;
    font-size: var(--text-base);
  }

  .privacy-settings__consent-body,
  .privacy-settings__consent-scope,
  .privacy-settings__consent-timestamp {
    margin: 0;
    color: var(--color-text-muted);
    line-height: 1.5;
  }

  .privacy-settings__consent-timestamp {
    font-size: var(--text-sm);
  }

  .privacy-settings__actions {
    display: flex;
    flex-wrap: wrap;
    gap: 0.65rem;
    margin-top: var(--space-3);
  }

  .privacy-settings__toggle-label {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    cursor: pointer;
    min-height: 2.75rem;
    padding-block: 0.25rem;
    user-select: none;
  }

  .privacy-settings__toggle {
    width: 1.25rem;
    height: 1.25rem;
    min-width: 1.25rem;
    cursor: pointer;
    accent-color: var(--color-primary);
  }

  .privacy-settings__modal-backdrop {
    position: fixed;
    inset: 0;
    z-index: 500;
    display: grid;
    place-items: center;
    padding: var(--space-4);
    background: color-mix(in srgb, var(--color-surface) 62%, transparent);
  }

  .privacy-settings__modal {
    width: min(100%, 28rem);
    display: flex;
    flex-direction: column;
    overflow: hidden;
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    background: var(--color-surface);
    box-shadow: var(--shadow-lg);
  }

  .privacy-settings__modal-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--space-3);
    padding: var(--space-3);
    border-bottom: 1px solid var(--color-border);
  }

  .privacy-settings__modal-head h2 {
    margin: 0;
    font-size: var(--text-base);
  }

  .privacy-settings__modal-body {
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
    padding: var(--space-4);
  }

  .privacy-settings__modal-body p {
    margin: 0;
    color: var(--color-text-muted);
    line-height: 1.5;
  }

  .privacy-settings__field {
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
    font-size: var(--text-sm);
    color: var(--color-text-muted);
  }

  .privacy-settings__field input {
    min-height: 2.75rem;
    border: 1px solid var(--color-border);
    border-radius: var(--radius-sm);
    padding: 0 var(--space-3);
    background: var(--color-surface);
    color: var(--color-text);
  }
</style>
