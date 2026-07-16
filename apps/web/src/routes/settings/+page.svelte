<script lang="ts">
  import { onMount } from 'svelte';
  import { _, locale } from 'svelte-i18n';
  import { goto } from '$app/navigation';
  import { auth, logout } from '$lib/stores/auth';
  import {
    devPhase,
    devForceVisualizations,
    devForceVisualizationsControl,
    devMode,
    type DevInsightMaturity,
  } from '$lib/stores/devMode';
  import { DEV_PHASE_PRESETS, type DevPhasePresetId } from '$lib/dev/phaseFixtures';
  import { setAppLocale, type AppLocale } from '$lib/i18n';
  import Button from '$lib/components/common/Button.svelte';
  import IconButton from '$lib/components/common/IconButton.svelte';
  import InlineAlert from '$lib/components/common/InlineAlert.svelte';
  import Panel from '$lib/components/common/Panel.svelte';
  import SegmentedControl, {
    type SegmentedControlOption,
  } from '$lib/components/common/SegmentedControl.svelte';
  import ScreenHeader from '$lib/components/common/ScreenHeader.svelte';
  import ThemeToggle from '$lib/components/common/ThemeToggle.svelte';
  import { ApiError } from '$lib/api/client';
  import { fetchDevInfo } from '$lib/api/dev';
  import { deleteAccount } from '$lib/api/user';
  import { downloadExport, exportFilename, saveBlob, type ExportKind } from '$lib/api/export';
  import {
    fetchUserPreferences,
    updateUserPreferences,
    type UserPreferencesResponse,
  } from '$lib/api/preferences';
  import { regenerateInsights } from '$lib/api/insights';
  import {
    fetchUserConsents,
    HEALTH_CONNECT_CONSENT_TYPE,
    HEALTH_CONNECT_CONSENT_VERSION,
    recordUserConsent,
    revokeUserConsent,
    type ConsentListResponse,
  } from '$lib/api/consents';
  import { getHealthConnectConsentStatus } from '$lib/healthConnect/consent';

  // ---------------------------------------------------------------------------
  // Export
  // ---------------------------------------------------------------------------
  let busy: ExportKind | null = null;
  let error = '';
  let preferences: UserPreferencesResponse | null = null;
  let preferencesBusy = false;
  let preferencesError = '';
  let regenerateBusy = false;
  let regenerateMessage = '';
  let regenerateError = '';
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

  async function handleDownload(kind: ExportKind): Promise<void> {
    busy = kind;
    error = '';
    try {
      const blob = await downloadExport(kind);
      saveBlob(blob, exportFilename(kind));
    } catch (err) {
      error = err instanceof Error ? err.message : $_('settings.export.error');
    } finally {
      busy = null;
    }
  }

  async function loadPreferences(): Promise<void> {
    if ($auth.status !== 'authenticated') return;
    try {
      preferences = await fetchUserPreferences();
    } catch (err) {
      preferencesError = err instanceof Error ? err.message : $_('settings.analysis.error');
    }
  }

  async function toggleAnalytics(enabled: boolean): Promise<void> {
    preferencesBusy = true;
    preferencesError = '';
    try {
      preferences = await updateUserPreferences({ analytics_enabled: enabled });
    } catch (err) {
      preferencesError = err instanceof Error ? err.message : $_('settings.analysis.error');
    } finally {
      preferencesBusy = false;
    }
  }

  async function toggleDigest(enabled: boolean): Promise<void> {
    preferencesBusy = true;
    preferencesError = '';
    try {
      preferences = await updateUserPreferences({ digest_enabled: enabled });
    } catch (err) {
      preferencesError = err instanceof Error ? err.message : $_('settings.analysis.error');
    } finally {
      preferencesBusy = false;
    }
  }

  async function handleRegenerateInsights(): Promise<void> {
    if (preferences?.analytics_enabled === false) return;
    regenerateBusy = true;
    regenerateMessage = '';
    regenerateError = '';
    try {
      const result = await regenerateInsights();
      regenerateMessage = $_('settings.analysis.regenerate_success', {
        values: { count: result.insight_count },
      });
    } catch (err) {
      if (err instanceof ApiError && err.status === 429) {
        regenerateError = $_('settings.analysis.regenerate_rate_limited');
      } else if (err instanceof ApiError && err.status === 403) {
        regenerateError = $_('settings.analysis.regenerate_disabled');
      } else {
        regenerateError =
          err instanceof Error ? err.message : $_('settings.analysis.regenerate_error');
      }
    } finally {
      regenerateBusy = false;
    }
  }

  function selectLocale(nextLocale: AppLocale): void {
    setAppLocale(nextLocale);
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

  // ---------------------------------------------------------------------------
  // Dev view availability (backend flag)
  // ---------------------------------------------------------------------------
  let devAvailable = false;
  const localeOptions: SegmentedControlOption[] = [
    { id: 'de', label: 'DE', testId: 'language-de' },
    { id: 'en', label: 'EN', testId: 'language-en' },
  ];
  const devInsightPhases: DevInsightMaturity[] = [
    'collecting',
    'early_patterns',
    'provisional',
    'robust',
  ];
  $: selectedDevPreset = DEV_PHASE_PRESETS[$devPhase.presetId];

  async function checkDevView(): Promise<void> {
    if ($auth.status !== 'authenticated') return;
    try {
      await fetchDevInfo();
      devAvailable = true;
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        devAvailable = false;
        return;
      }
      devAvailable = false;
    }
  }

  // ---------------------------------------------------------------------------
  // 7× tap on version string (ADR-0019)
  // ---------------------------------------------------------------------------
  const REQUIRED_TAPS = 7;
  const TAP_TIMEOUT_MS = 3000;

  let tapCount = 0;
  let tapTimer: ReturnType<typeof setTimeout> | null = null;
  let toastMessage = '';
  let toastVisible = false;
  let toastTimer: ReturnType<typeof setTimeout> | null = null;

  function showToast(msg: string) {
    toastMessage = msg;
    toastVisible = true;
    if (toastTimer) clearTimeout(toastTimer);
    toastTimer = setTimeout(() => {
      toastVisible = false;
    }, 2500);
  }

  function handleVersionTap() {
    tapCount++;
    if (tapTimer) clearTimeout(tapTimer);

    if (tapCount >= REQUIRED_TAPS) {
      tapCount = 0;
      devMode.toggle();
      showToast(
        $devMode ? $_('settings.developer.toast_enabled') : $_('settings.developer.toast_disabled')
      );
      return;
    }

    tapTimer = setTimeout(() => {
      tapCount = 0;
    }, TAP_TIMEOUT_MS);
  }

  function updateDevEntryCount(value: string): void {
    const parsed = Number.parseInt(value, 10);
    devPhase.setEntryCount(Number.isFinite(parsed) ? parsed : 0);
  }

  onMount(() => {
    void checkDevView();
    void loadPreferences();
    void loadConsents();
  });
</script>

<svelte:head>
  <title>{$_('settings.title')} - {$_('app.name')}</title>
</svelte:head>

<main class="settings screen-stack">
  <ScreenHeader title={$_('settings.title')} subtitle={$_('settings.subtitle')} />

  {#if $auth.status !== 'authenticated'}
    <Panel variant="bordered">
      <p>{$_('settings.auth_required')}</p>
      <Button href="/auth/login" variant="primary" size="sm">{$_('auth.login.submit')}</Button>
    </Panel>
  {:else}
    <section class="settings__panel" data-testid="settings-section-vocabulary">
      <div class="settings__panel-head">
        <span class="settings__section-kicker">{$_('settings.section.vocabulary')}</span>
        <h2>{$_('settings.vocabulary.heading')}</h2>
        <p>{$_('settings.vocabulary.body')}</p>
      </div>
      <div class="settings__vocabulary-grid">
        <a
          class="settings__vocabulary-card"
          href="/settings/tags"
          data-testid="settings-vocab-tags"
        >
          <strong>{$_('settings.vocabulary.tags')}</strong>
          <span>{$_('settings.vocabulary.tags_body')}</span>
        </a>
        <a
          class="settings__vocabulary-card"
          href="/settings/symptoms"
          data-testid="settings-vocab-symptoms"
        >
          <strong>{$_('settings.vocabulary.symptoms')}</strong>
          <span>{$_('settings.vocabulary.symptoms_body')}</span>
        </a>
        <a
          class="settings__vocabulary-card"
          href="/settings/tags"
          data-testid="settings-vocab-habits"
        >
          <strong>{$_('settings.vocabulary.habits')}</strong>
          <span>{$_('settings.vocabulary.habits_body')}</span>
        </a>
      </div>
    </section>

    <section class="settings__panel" data-testid="settings-section-export">
      <div class="settings__panel-head">
        <span class="settings__section-kicker">{$_('settings.section.export')}</span>
        <h2>{$_('settings.export.heading')}</h2>
        <p>{$_('settings.export.body')}</p>
      </div>
      <div class="settings__actions">
        <Button
          variant="primary"
          type="button"
          loading={busy === 'zip'}
          disabled={busy !== null}
          on:click={() => handleDownload('zip')}
        >
          {busy === 'zip' ? $_('settings.export.busy') : $_('settings.export.zip')}
        </Button>
        <Button
          variant="secondary"
          type="button"
          loading={busy === 'json'}
          disabled={busy !== null}
          on:click={() => handleDownload('json')}
        >
          {busy === 'json' ? $_('settings.export.busy') : $_('settings.export.json')}
        </Button>
        <Button
          variant="secondary"
          type="button"
          loading={busy === 'csv'}
          disabled={busy !== null}
          on:click={() => handleDownload('csv')}
        >
          {busy === 'csv' ? $_('settings.export.busy') : $_('settings.export.csv')}
        </Button>
      </div>
      {#if error}
        <InlineAlert variant="error" message={error} />
      {/if}
    </section>

    <section class="settings__panel" data-testid="settings-section-analysis">
      <div class="settings__panel-head">
        <span class="settings__section-kicker">{$_('settings.section.analysis')}</span>
        <h2>{$_('settings.analysis.heading')}</h2>
        <p>{$_('settings.analysis.body')}</p>
      </div>
      <label class="settings__toggle-label">
        <input
          type="checkbox"
          class="settings__toggle"
          checked={preferences?.analytics_enabled ?? true}
          disabled={preferencesBusy}
          data-testid="analytics-toggle"
          on:change={(e) => void toggleAnalytics(e.currentTarget.checked)}
        />
        <span>{$_('settings.analysis.analytics_enabled')}</span>
      </label>
      <label class="settings__toggle-label">
        <input
          type="checkbox"
          class="settings__toggle"
          checked={preferences?.digest_enabled ?? true}
          disabled={preferencesBusy || preferences?.analytics_enabled === false}
          data-testid="digest-toggle"
          on:change={(e) => void toggleDigest(e.currentTarget.checked)}
        />
        <span>{$_('settings.analysis.digest_enabled')}</span>
      </label>
      <p class="settings__analysis-note">{$_('settings.analysis.digest_hint')}</p>
      <p class="settings__analysis-note">
        <a href="/insights/digest" data-testid="digest-preview-link">
          {$_('settings.analysis.digest_preview_link')}
        </a>
      </p>
      {#if preferencesError}
        <InlineAlert variant="error" message={preferencesError} />
      {/if}
      <div class="settings__actions">
        <Button
          variant="secondary"
          type="button"
          data-testid="regenerate-insights"
          loading={regenerateBusy}
          disabled={preferencesBusy || preferences?.analytics_enabled === false}
          on:click={() => void handleRegenerateInsights()}
        >
          {$_('settings.analysis.regenerate_insights')}
        </Button>
      </div>
      <p class="settings__analysis-note">{$_('settings.analysis.regenerate_hint')}</p>
      {#if regenerateMessage}
        <InlineAlert variant="success" message={regenerateMessage} />
      {/if}
      {#if regenerateError}
        <InlineAlert variant="error" message={regenerateError} />
      {/if}
    </section>

    <section class="settings__panel" data-testid="settings-section-privacy">
      <div class="settings__panel-head">
        <span class="settings__section-kicker">{$_('settings.section.privacy')}</span>
        <h2>{$_('settings.privacy.heading')}</h2>
        <p>{$_('settings.privacy.body')}</p>
      </div>
      <p class="settings__privacy-note">{$_('settings.privacy.policy_body')}</p>

      <div class="settings__consent-block" data-testid="settings-health-connect-consent">
        <h3 class="settings__consent-heading">{$_('settings.privacy.health_connect.heading')}</h3>
        <p class="settings__consent-body">{$_('settings.privacy.health_connect.body')}</p>
        <p class="settings__consent-scope">{$_('settings.privacy.health_connect.scope')}</p>
        <p class="settings__consent-scope" data-testid="health-connect-deferred-note">
          {$_('settings.privacy.health_connect.deferred_note')}
        </p>
        {#if healthConnectGranted && healthConnectConsent?.updated_at}
          <p class="settings__consent-timestamp" data-testid="health-connect-consent-timestamp">
            {$_('settings.privacy.health_connect.granted_at', {
              values: { timestamp: formatConsentTimestamp(healthConnectConsent.updated_at) },
            })}
          </p>
        {/if}
        {#if !healthConnectGranted}
          <label class="settings__toggle-label">
            <input
              type="checkbox"
              class="settings__toggle"
              bind:checked={healthConnectGrantChecked}
              disabled={consentsBusy}
              data-testid="health-connect-consent-checkbox"
            />
            <span>{$_('settings.privacy.health_connect.grant_label')}</span>
          </label>
          <div class="settings__actions">
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
          <div class="settings__actions">
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

      <div class="settings__actions">
        <Button href="/privacy" variant="secondary" data-testid="settings-privacy-policy">
          {$_('settings.privacy.policy_link')}
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
    </section>

    <section class="settings__panel" data-testid="settings-section-appearance">
      <div class="settings__panel-head">
        <span class="settings__section-kicker">{$_('settings.section.appearance')}</span>
        <h2>{$_('settings.appearance.heading')}</h2>
        <p>{$_('settings.appearance.body')}</p>
      </div>
      <div class="settings__appearance-row">
        <span>{$_('settings.appearance.theme')}</span>
        <ThemeToggle testId="settings-theme-toggle-panel" />
      </div>
      <SegmentedControl
        value={$locale ?? 'de'}
        options={localeOptions}
        ariaLabel={$_('settings.appearance.language')}
        testId="settings-language-control"
        equalWidth={false}
        on:change={(event) => selectLocale(event.detail.value as AppLocale)}
      />
      <div class="settings__actions">
        <Button href="/settings/app" variant="secondary">{$_('settings.app.open')}</Button>
      </div>
    </section>

    <section class="settings__panel" data-testid="settings-section-account">
      <div class="settings__panel-head">
        <span class="settings__section-kicker">{$_('settings.section.account')}</span>
        <h2>{$_('settings.account.heading')}</h2>
        <p>{$_('settings.account.body')}</p>
      </div>
      <div class="settings__actions">
        <Button variant="ghost" data-testid="settings-logout" on:click={() => void handleLogout()}>
          {$_('auth.logout.label')}
        </Button>
      </div>
    </section>

    <!-- DEVELOPER section: only visible when devMode is active -->
    {#if $devMode || devAvailable}
      <section class="settings__panel settings__panel--developer" data-testid="developer-section">
        <div class="settings__panel-head">
          <span class="settings__section-kicker">{$_('settings.section.developer')}</span>
          <h2>{$_('settings.developer.heading')}</h2>
          <p>{$_('settings.developer.body')}</p>
        </div>
        <div class="settings__actions">
          <Button href="/dev" variant="secondary" data-testid="dev-link">
            {$_('settings.dev.open')}
          </Button>
        </div>
        <label class="settings__toggle-label">
          <input
            type="checkbox"
            class="settings__toggle"
            checked={$devMode}
            aria-label={$_('settings.developer.toggle_aria')}
            data-testid="developer-toggle"
            on:change={(e) => devMode.set(e.currentTarget.checked)}
          />
          <span>{$_('settings.developer.toggle_label')}</span>
        </label>
        {#if $devMode}
          <label class="settings__toggle-label">
            <input
              type="checkbox"
              class="settings__toggle"
              checked={$devForceVisualizations}
              aria-label={$_('settings.developer.force_viz_aria')}
              data-testid="force-viz-toggle"
              on:change={(e) => devForceVisualizationsControl.set(e.currentTarget.checked)}
            />
            <span>{$_('settings.developer.force_viz_label')}</span>
          </label>
          <div class="settings__dev-grid" data-testid="developer-phase-controls">
            <label class="settings__field">
              <span>{$_('settings.developer.phase_label')}</span>
              <select
                value={$devPhase.presetId}
                data-testid="developer-phase-select"
                on:change={(e) => devPhase.setPreset(e.currentTarget.value as DevPhasePresetId)}
              >
                {#each devInsightPhases as phase}
                  <option value={phase}>{$_(`settings.developer.phase.${phase}`)}</option>
                {/each}
              </select>
            </label>
          </div>
          <p class="settings__dev-summary" data-testid="developer-phase-summary">
            {$_(selectedDevPreset.coverageKey, {
              values: { count: $devPhase.entryCount },
            })}
          </p>
          <details class="settings__dev-advanced">
            <summary>{$_('settings.developer.advanced')}</summary>
            <div class="settings__dev-grid">
              <label class="settings__field">
                <span>{$_('settings.developer.entry_count_label')}</span>
                <input
                  type="number"
                  min="0"
                  max="200"
                  value={$devPhase.entryCount}
                  data-testid="developer-entry-count"
                  on:input={(e) => updateDevEntryCount(e.currentTarget.value)}
                />
              </label>
              <label class="settings__toggle-label">
                <input
                  type="checkbox"
                  class="settings__toggle"
                  checked={$devPhase.onboardingCompleted}
                  data-testid="developer-onboarding-toggle"
                  on:change={(e) => devPhase.setOnboardingCompleted(e.currentTarget.checked)}
                />
                <span>{$_('settings.developer.onboarding_completed')}</span>
              </label>
            </div>
          </details>
          <div class="settings__actions">
            <Button
              variant="secondary"
              data-testid="developer-onboarding-preview"
              on:click={() => devPhase.setOnboardingPreviewOpen(true)}
            >
              {$_('settings.developer.preview_onboarding')}
            </Button>
          </div>
        {/if}
      </section>
    {/if}
  {/if}

  <!-- Version string: hidden tap target for 7× dev mode activation (ADR-0019) -->
  <footer class="settings__footer">
    <!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
    <!-- svelte-ignore a11y-click-events-have-key-events -->
    <p
      class="settings__version"
      role="contentinfo"
      data-testid="version-string"
      on:click={handleVersionTap}
    >
      {$_('app.name')} v{$_('app.version')}
    </p>
  </footer>
</main>

<!-- Toast notification -->
{#if toastVisible}
  <div class="settings__toast" role="status" aria-live="polite" data-testid="dev-toast">
    {toastMessage}
  </div>
{/if}

{#if deleteDialogOpen}
  <div
    class="settings__modal-backdrop"
    role="presentation"
    data-testid="settings-delete-backdrop"
    on:click={closeDeleteDialog}
  >
    <dialog
      open
      class="settings__modal settings__modal--compact"
      aria-modal="true"
      aria-labelledby="delete-account-title"
      data-testid="settings-delete-dialog"
      on:click|stopPropagation
    >
      <div class="settings__modal-head">
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
      <div class="settings__delete-body">
        <p>{$_('settings.privacy.delete_body')}</p>
        <label class="settings__field">
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
        <div class="settings__actions">
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

{#if $devMode && $devPhase.onboardingPreviewOpen}
  <div
    class="settings__modal-backdrop"
    role="presentation"
    on:click={() => devPhase.setOnboardingPreviewOpen(false)}
  >
    <dialog
      open
      class="settings__modal"
      aria-modal="true"
      aria-labelledby="onboarding-preview-title"
      on:click|stopPropagation
    >
      <div class="settings__modal-head">
        <h2 id="onboarding-preview-title">{$_('settings.developer.preview_title')}</h2>
        <IconButton
          type="button"
          ariaLabel={$_('settings.developer.preview_close')}
          title={$_('settings.developer.preview_close')}
          on:click={() => devPhase.setOnboardingPreviewOpen(false)}
        >
          x
        </IconButton>
      </div>
      <iframe
        class="settings__preview-frame"
        title={$_('settings.developer.preview_title')}
        src="/onboarding?preview=1"
      ></iframe>
    </dialog>
  </div>
{/if}

<style>
  .settings {
    width: min(100%, 46rem);
    margin: 0 auto;
    display: flex;
    flex-direction: column;
  }

  .settings__panel-head p {
    margin: var(--space-1) 0 0;
    opacity: 0.72;
  }

  .settings__privacy-note {
    margin: 0;
    color: var(--color-text-muted);
    line-height: 1.5;
  }

  .settings__consent-block {
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
    padding: var(--space-3);
    border-radius: var(--radius-sm);
    border: 1px solid var(--color-border-chart);
    background: var(--color-surface);
  }

  .settings__consent-heading {
    margin: 0;
    font-size: var(--text-base);
  }

  .settings__consent-body,
  .settings__consent-scope,
  .settings__consent-timestamp {
    margin: 0;
    color: var(--color-text-muted);
    line-height: 1.5;
  }

  .settings__consent-timestamp {
    font-size: var(--text-sm);
  }

  .settings__panel {
    display: flex;
    flex-direction: column;
    gap: var(--screen-gap);
    padding: var(--space-4);
    border-radius: var(--radius-md);
    background: var(--color-surface-chart-bg);
    border: 1px solid var(--color-border-chart);
  }

  .settings__panel--developer {
    border-color: var(--color-primary);
  }

  .settings__panel-head h2 {
    margin: 0;
    font-size: var(--text-lg, 1.125rem);
  }

  .settings__section-kicker {
    display: inline-block;
    margin-bottom: var(--space-1);
    font-size: var(--text-xs);
    font-weight: 700;
    color: var(--color-text-muted);
    letter-spacing: 0.06em;
    text-transform: uppercase;
  }

  .settings__actions {
    display: flex;
    flex-wrap: wrap;
    gap: 0.65rem;
  }

  .settings__analysis-note {
    margin: 0;
    color: var(--color-text-muted);
    font-size: var(--text-sm);
    line-height: 1.5;
  }

  .settings__vocabulary-grid {
    display: grid;
    gap: var(--space-3);
    grid-template-columns: repeat(auto-fit, minmax(12rem, 1fr));
  }

  .settings__vocabulary-card {
    display: flex;
    flex-direction: column;
    gap: var(--space-1);
    min-height: 5.5rem;
    padding: var(--space-3);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    background: var(--color-surface);
    color: inherit;
    text-decoration: none;
    transition:
      border-color var(--transition-fast),
      background-color var(--transition-fast);
  }

  .settings__vocabulary-card:hover {
    border-color: color-mix(in srgb, var(--color-primary) 35%, var(--color-border));
    background: color-mix(in srgb, var(--color-primary-soft) 28%, var(--color-surface));
  }

  .settings__vocabulary-card strong {
    font-size: var(--text-base);
  }

  .settings__vocabulary-card span {
    font-size: var(--text-sm);
    color: var(--color-text-muted);
    line-height: 1.45;
  }

  .settings__delete-body {
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
    padding: var(--space-4);
  }

  .settings__delete-body p {
    margin: 0;
    color: var(--color-text-muted);
    line-height: 1.5;
  }

  .settings__modal--compact {
    width: min(100%, 28rem);
    height: auto;
    max-height: min(88dvh, 28rem);
  }

  /* Developer Mode toggle — min 44px touch target */
  .settings__toggle-label {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    cursor: pointer;
    min-height: 2.75rem;
    padding-block: 0.25rem;
    user-select: none;
  }

  .settings__toggle {
    width: 1.25rem;
    height: 1.25rem;
    min-width: 1.25rem;
    cursor: pointer;
    accent-color: var(--color-primary);
  }

  .settings__dev-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(12rem, 1fr));
    gap: var(--space-3);
  }

  .settings__field {
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
    font-size: var(--text-sm);
    color: var(--color-text-muted);
  }

  .settings__field select,
  .settings__field input {
    min-height: 44px;
    border: 1px solid var(--color-border);
    border-radius: var(--radius-sm);
    padding: 0 var(--space-3);
    background: var(--color-surface);
    color: var(--color-text);
  }

  .settings__dev-summary {
    margin: 0;
    color: var(--color-text-muted);
    font-size: var(--text-sm);
    line-height: 1.5;
  }

  .settings__dev-advanced {
    display: grid;
    gap: var(--space-3);
  }

  .settings__dev-advanced summary {
    min-height: 44px;
    display: flex;
    align-items: center;
    cursor: pointer;
    color: var(--color-text-muted);
    font-size: var(--text-sm);
    font-weight: 700;
  }

  .settings__modal-backdrop {
    position: fixed;
    inset: 0;
    z-index: 500;
    display: grid;
    place-items: center;
    padding: var(--space-4);
    background: color-mix(in srgb, var(--color-surface) 62%, transparent);
  }

  .settings__modal {
    width: min(100%, 42rem);
    height: min(88dvh, 52rem);
    display: flex;
    flex-direction: column;
    overflow: hidden;
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    background: var(--color-surface);
    box-shadow: var(--shadow-lg);
  }

  .settings__modal-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--space-3);
    padding: var(--space-3);
    border-bottom: 1px solid var(--color-border);
  }

  .settings__modal-head h2 {
    margin: 0;
    font-size: var(--text-base);
  }

  .settings__preview-frame {
    flex: 1;
    width: 100%;
    border: 0;
    background: var(--color-surface);
  }

  .settings__appearance-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--space-3);
  }

  /* Footer version string — no visible affordance */
  .settings__footer {
    margin-top: var(--space-4, 1rem);
    text-align: center;
  }

  .settings__version {
    font-size: var(--text-xs, 0.75rem);
    color: var(--color-text-muted);
    cursor: default;
    user-select: none;
    margin: 0;
  }

  /* Toast */
  .settings__toast {
    position: fixed;
    bottom: var(--space-6, 1.5rem);
    left: 50%;
    transform: translateX(-50%);
    background: var(--color-surface-2);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md, 0.5rem);
    padding: var(--space-3, 0.75rem) var(--space-5, 1.25rem);
    font-size: var(--text-sm, 0.875rem);
    color: var(--color-text);
    box-shadow: var(--shadow-lg);
    z-index: 300;
    white-space: nowrap;
    animation: toastIn 180ms cubic-bezier(0.16, 1, 0.3, 1) both;
  }

  @keyframes toastIn {
    from {
      opacity: 0;
      transform: translateX(-50%) translateY(8px);
    }
    to {
      opacity: 1;
      transform: translateX(-50%) translateY(0);
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .settings__toast {
      animation: none;
    }
  }
</style>
