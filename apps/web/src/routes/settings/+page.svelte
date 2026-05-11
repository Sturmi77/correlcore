<script lang="ts">
  import { onMount } from 'svelte';
  import { _ } from 'svelte-i18n';
  import { auth } from '$lib/stores/auth';
  import { developerMode } from '$lib/stores/developerMode';
  import ThemeToggle from '$lib/components/common/ThemeToggle.svelte';
  import { ApiError } from '$lib/api/client';
  import { fetchDevInfo } from '$lib/api/dev';
  import { downloadExport, exportFilename, saveBlob, type ExportKind } from '$lib/api/export';

  let busy: ExportKind | null = null;
  let error = '';
  let devAvailable = false;

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

    <!-- Developer section: visible when backend devAvailable OR user toggled developerMode -->
    {#if devAvailable || $developerMode}
      <section class="settings__panel">
        <div class="settings__panel-head">
          <h2>{$_('settings.dev.heading')}</h2>
          <p>{$_('settings.dev.body')}</p>
        </div>
        <div class="settings__downloads">
          <a class="btn variant-soft-primary" href="/dev">{$_('settings.dev.open')}</a>
        </div>
      </section>
    {/if}

    <!-- Developer Mode toggle (always visible for authenticated users) -->
    <section class="settings__panel">
      <div class="settings__panel-head">
        <h2>{$_('settings.developer.heading')}</h2>
        <p>{$_('settings.developer.body')}</p>
      </div>
      <label class="settings__toggle-label">
        <input
          type="checkbox"
          class="settings__toggle"
          checked={$developerMode}
          aria-label={$_('settings.developer.toggle_aria')}
          on:change={(e) => developerMode.set(e.currentTarget.checked)}
        />
        <span>{$_('settings.developer.toggle_label')}</span>
      </label>
      {#if $developerMode}
        <p class="settings__hint">{$_('settings.developer.active_hint')}</p>
      {/if}
    </section>

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
</main>

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

  /* Phase 1 fix: replace old rgb(var(--color-surface-*)) syntax with correct design tokens */
  .settings__panel {
    display: flex;
    flex-direction: column;
    gap: 1rem;
    padding: 1rem;
    border-radius: 0.5rem;
    background: var(--color-surface-chart-bg);
    border: 1px solid var(--color-border-chart);
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

  /* Phase 1 fix: replace hardcoded #b91c1c with design token */
  .settings__error {
    margin: 0;
    color: var(--color-error);
  }

  .settings__hint {
    margin: 0;
    font-size: var(--text-sm, 0.875rem);
    color: var(--color-text-muted);
  }

  /* Phase 3: Developer Mode toggle — min 44px touch target */
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
</style>
