<script lang="ts">
  import { onMount } from 'svelte';
  import { _ } from 'svelte-i18n';
  import { auth } from '$lib/stores/auth';
  import { devMode } from '$lib/stores/devMode';
  import ThemeToggle from '$lib/components/common/ThemeToggle.svelte';
  import { ApiError } from '$lib/api/client';
  import { fetchDevInfo } from '$lib/api/dev';
  import { downloadExport, exportFilename, saveBlob, type ExportKind } from '$lib/api/export';

  // ---------------------------------------------------------------------------
  // Export
  // ---------------------------------------------------------------------------
  let busy: ExportKind | null = null;
  let error = '';

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
  });
</script>

<svelte:head>
  <title>{$_('settings.title')} - {$_('app.name')}</title>
</svelte:head>

<main class="settings">
  <header class="settings__top">
    <a class="btn btn-sm variant-ghost-surface" href="/">{$_('nav.home')}</a>
    <ThemeToggle testId="settings-theme-toggle" />
  </header>

  <section class="settings__intro">
    <h1>{$_('settings.title')}</h1>
    <p>{$_('settings.subtitle')}</p>
  </section>

  {#if $auth.status !== 'authenticated'}
    <section class="settings__panel">
      <p>{$_('settings.auth_required')}</p>
      <a class="btn btn-sm variant-filled-primary" href="/auth/login">{$_('auth.login.submit')}</a>
    </section>
  {:else}
    <section class="settings__panel">
      <div class="settings__panel-head">
        <h2>{$_('settings.tags.heading')}</h2>
        <p>{$_('settings.tags.body')}</p>
      </div>
      <div class="settings__downloads">
        <a class="btn variant-soft-primary" href="/settings/tags">{$_('settings.tags.open')}</a>
      </div>
    </section>

    <!-- DEVELOPER section: only visible when devMode is active -->
    {#if $devMode || devAvailable}
      <section class="settings__panel settings__panel--developer" data-testid="developer-section">
        <div class="settings__panel-head">
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
      </section>
    {/if}

    <section class="settings__panel">
      <div class="settings__panel-head">
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
      </div>
      {#if error}
        <p class="settings__error" role="alert">{error}</p>
      {/if}
    </section>
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

  .settings__top {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .settings__intro h1 {
    margin: 0;
    font-size: var(--text-2xl, 1.5rem);
  }

  .settings__intro p,
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

  .settings__downloads {
    display: flex;
    flex-wrap: wrap;
    gap: 0.65rem;
  }

  .settings__error {
    margin: 0;
    color: var(--color-error);
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
