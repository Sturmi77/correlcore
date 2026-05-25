<script lang="ts">
  import { onMount } from 'svelte';
  import { _, locale } from 'svelte-i18n';
  import { goto } from '$app/navigation';
  import { auth, logout } from '$lib/stores/auth';
  import {
    devForceVisualizations,
    devForceVisualizationsControl,
    devMode,
  } from '$lib/stores/devMode';
  import { setAppLocale, type AppLocale } from '$lib/i18n';
  import Button from '$lib/components/common/Button.svelte';
  import InlineAlert from '$lib/components/common/InlineAlert.svelte';
  import Panel from '$lib/components/common/Panel.svelte';
  import ScreenHeader from '$lib/components/common/ScreenHeader.svelte';
  import ThemeToggle from '$lib/components/common/ThemeToggle.svelte';
  import { ApiError } from '$lib/api/client';
  import { fetchDevInfo } from '$lib/api/dev';
  import { downloadExport, exportFilename, saveBlob, type ExportKind } from '$lib/api/export';
  import {
    fetchUserPreferences,
    updateUserPreferences,
    type UserPreferencesResponse,
  } from '$lib/api/preferences';

  // ---------------------------------------------------------------------------
  // Export
  // ---------------------------------------------------------------------------
  let busy: ExportKind | null = null;
  let error = '';
  let preferences: UserPreferencesResponse | null = null;
  let preferencesBusy = false;
  let preferencesError = '';

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

  function selectLocale(nextLocale: AppLocale): void {
    setAppLocale(nextLocale);
  }

  async function handleLogout(): Promise<void> {
    await logout();
    await goto('/', { replaceState: true });
  }

  // ---------------------------------------------------------------------------
  // Dev view availability (backend flag)
  // ---------------------------------------------------------------------------
  let devAvailable = false;

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

  onMount(() => {
    void checkDevView();
    void loadPreferences();
  });
</script>

<svelte:head>
  <title>{$_('settings.title')} - {$_('app.name')}</title>
</svelte:head>

<main class="settings">
  <ScreenHeader title={$_('settings.title')} subtitle={$_('settings.subtitle')} />

  {#if $auth.status !== 'authenticated'}
    <Panel variant="bordered">
      <p>{$_('settings.auth_required')}</p>
      <Button href="/auth/login" variant="primary" size="sm">{$_('auth.login.submit')}</Button>
    </Panel>
  {:else}
    <section class="settings__panel" data-testid="settings-section-tracking">
      <div class="settings__panel-head">
        <span class="settings__section-kicker">{$_('settings.section.tracking')}</span>
        <h2>{$_('settings.tracking.heading')}</h2>
        <p>{$_('settings.tracking.body')}</p>
      </div>
      <div class="settings__downloads">
        <a class="btn variant-soft-primary" href="/settings/tags">{$_('settings.tags.open')}</a>
        <button class="btn variant-ghost-surface" type="button" disabled>
          {$_('settings.tracking.symptoms_placeholder')}
        </button>
        <button class="btn variant-ghost-surface" type="button" disabled>
          {$_('settings.tracking.reminders_placeholder')}
        </button>
      </div>
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
      <div class="settings__downloads">
        <a class="btn variant-soft-primary" href="/insights">{$_('settings.analysis.insights')}</a>
      </div>
      {#if preferencesError}
        <InlineAlert variant="error" message={preferencesError} />
      {/if}
    </section>

    <section class="settings__panel" data-testid="settings-section-privacy">
      <div class="settings__panel-head">
        <span class="settings__section-kicker">{$_('settings.section.privacy')}</span>
        <h2>{$_('settings.export.heading')}</h2>
        <p>{$_('settings.export.body')}</p>
      </div>
      <div class="settings__downloads">
        <button
          class="btn variant-filled-primary"
          type="button"
          disabled={busy !== null}
          on:click={() => handleDownload('zip')}
        >
          {busy === 'zip' ? $_('settings.export.busy') : $_('settings.export.zip')}
        </button>
        <button
          class="btn variant-soft-primary"
          type="button"
          disabled={busy !== null}
          on:click={() => handleDownload('json')}
        >
          {busy === 'json' ? $_('settings.export.busy') : $_('settings.export.json')}
        </button>
        <button
          class="btn variant-soft-primary"
          type="button"
          disabled={busy !== null}
          on:click={() => handleDownload('csv')}
        >
          {busy === 'csv' ? $_('settings.export.busy') : $_('settings.export.csv')}
        </button>
        <button class="btn variant-ghost-surface" type="button" disabled>
          {$_('settings.privacy.delete_placeholder')}
        </button>
      </div>
      {#if error}
        <InlineAlert variant="error" message={error} />
      {/if}
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
      <div class="settings__language" role="group" aria-label={$_('settings.appearance.language')}>
        <button
          type="button"
          class:active={$locale === 'de'}
          data-testid="language-de"
          on:click={() => selectLocale('de')}
        >
          DE
        </button>
        <button
          type="button"
          class:active={$locale === 'en'}
          data-testid="language-en"
          on:click={() => selectLocale('en')}
        >
          EN
        </button>
      </div>
    </section>

    <section class="settings__panel" data-testid="settings-section-account">
      <div class="settings__panel-head">
        <span class="settings__section-kicker">{$_('settings.section.account')}</span>
        <h2>{$_('settings.account.heading')}</h2>
        <p>{$_('settings.account.body')}</p>
      </div>
      <div class="settings__downloads">
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
        <div class="settings__downloads">
          <a class="btn variant-soft-primary" href="/dev" data-testid="dev-link">
            {$_('settings.dev.open')}
          </a>
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

<style>
  .settings {
    width: min(100%, 46rem);
    margin: 0 auto;
    padding: 1.25rem;
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .settings__panel-head p {
    margin: 0.25rem 0 0;
    opacity: 0.72;
  }

  .settings__panel {
    display: flex;
    flex-direction: column;
    gap: 1rem;
    padding: 1rem;
    border-radius: 0.5rem;
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

  .settings__downloads {
    display: flex;
    flex-wrap: wrap;
    gap: 0.65rem;
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

  .settings__appearance-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--space-3);
  }

  .settings__language {
    display: inline-flex;
    width: fit-content;
    gap: 0.25rem;
    padding: 0.25rem;
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    background: var(--color-surface);
  }

  .settings__language button {
    min-height: 44px;
    border-radius: var(--radius-sm);
    padding: 0 var(--space-4);
    color: var(--color-text-muted);
  }

  .settings__language button.active {
    color: var(--color-text-inverse);
    background: var(--color-primary);
  }

  /* Footer version string — no visible affordance */
  .settings__footer {
    margin-top: var(--space-4, 1rem);
    text-align: center;
  }

  .settings__version {
    font-size: var(--text-xs, 0.75rem);
    color: var(--color-text-faint);
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
